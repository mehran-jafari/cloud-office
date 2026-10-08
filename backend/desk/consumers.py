import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import Device, DeskSession


class DeskSignalConsumer(AsyncWebsocketConsumer):
    """سیگنالینگ WebRTC شبیه DeskHost / AnyDesk — توکن دستگاه از subprotocol
    WebSocket (هرگز از query string که در لاگ‌ها نشت می‌کند)."""

    async def connect(self):
        # subprotocols: ['desk_token', '<device-token-hex>']
        subs = [s.decode('utf-8', errors='ignore') if isinstance(s, bytes) else s
                for s in self.scope.get('subprotocols', [])]
        token = subs[1] if len(subs) >= 2 and subs[0] == 'desk_token' else ''
        self.device = await self.get_device(token)
        if not self.device:
            await self.close(code=4001)
            return

        self.desk_id = self.device.desk_id
        self.group_name = f'desk_{self.desk_id}'
        self.conference_codes = set()

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        # accept with the subprotocol we negotiated
        await self.accept(subprotocol='desk_token' if token else None)
        await self.set_online(True)
        await self.send_json({
            'type': 'registered',
            'desk_id': self.desk_id,
            'alias': self.device.alias,
        })

    async def disconnect(self, _code):
        if not getattr(self, 'desk_id', None):
            return
        await self.set_online(False)
        for code in list(getattr(self, 'conference_codes', set())):
            await self.leave_conference(code)
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = payload.get('type')
        if msg_type == 'ping':
            await self.send_json({'type': 'pong'})
            await self.touch()
            return

        # رله سیگنال WebRTC بین دو desk_id
        if msg_type in {'offer', 'answer', 'ice', 'control', 'session_update'}:
            target = payload.get('to') or payload.get('target')
            if not target:
                return
            out = dict(payload)
            out['from'] = self.desk_id
            await self.channel_layer.group_send(
                f'desk_{target}',
                {'type': 'signal.message', 'payload': out},
            )
            return

        if msg_type == 'conf_join':
            await self.join_conference(payload.get('code'), payload.get('alias'))
            return

        if msg_type == 'conf_leave':
            await self.leave_conference(payload.get('code'))
            return

        if msg_type in {'conf_offer', 'conf_answer', 'conf_ice'}:
            code = payload.get('code')
            if not code or code not in self.conference_codes:
                return
            out = dict(payload)
            out['from'] = self.desk_id
            await self.channel_layer.group_send(
                f'conf_{code}',
                {'type': 'conf.message', 'payload': out},
            )
            return

    async def signal_message(self, event):
        await self.send_json(event['payload'])

    async def conf_message(self, event):
        await self.send_json(event['payload'])

    async def join_conference(self, code, alias=None):
        if not code:
            return
        code = str(code).upper()
        self.conference_codes.add(code)
        await self.channel_layer.group_add(f'conf_{code}', self.channel_name)
        await self.channel_layer.group_send(
            f'conf_{code}',
            {
                'type': 'conf.message',
                'payload': {
                    'type': 'conf_peer_join',
                    'code': code,
                    'desk_id': self.desk_id,
                    'alias': alias or self.device.alias,
                },
            },
        )

    async def leave_conference(self, code):
        if not code or code not in self.conference_codes:
            return
        self.conference_codes.discard(code)
        await self.channel_layer.group_send(
            f'conf_{code}',
            {
                'type': 'conf.message',
                'payload': {
                    'type': 'conf_peer_leave',
                    'code': code,
                    'desk_id': self.desk_id,
                },
            },
        )
        await self.channel_layer.group_discard(f'conf_{code}', self.channel_name)

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content, ensure_ascii=False))

    @database_sync_to_async
    def get_device(self, token):
        if not token:
            return None
        return Device.objects.filter(token=token).first()

    @database_sync_to_async
    def set_online(self, online):
        Device.objects.filter(pk=self.device.pk).update(
            online=online, last_seen=timezone.now()
        )

    @database_sync_to_async
    def touch(self):
        Device.objects.filter(pk=self.device.pk).update(last_seen=timezone.now())
