import uuid
import logging
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import Message
from .remote_models import RemoteSession

logger = logging.getLogger(__name__)

class RemoteConferenceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = int(self.scope['url_route']['kwargs']['session_id']); self.group_name = f'remote_session_{self.session_id}'
        user = self.scope.get('user'); session = await self.authorized_session(user.id if user else None)
        if not user or not user.is_authenticated or not session:
            logger.warning('webrtc.connect_denied session_id=%s user_id=%s', self.session_id, getattr(user, 'id', None))
            await self.close(code=4403); return
        self.user_id = user.id; self.user_name = user.get_full_name() or user.username
        logger.info('webrtc.connected session_id=%s user_id=%s', self.session_id, self.user_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name); await self.accept(subprotocol='access_token')
        await self.channel_layer.group_send(self.group_name, {'type': 'remote.event', 'event_type': 'peer.joined', 'user_id': self.user_id, 'sender': self.channel_name})
        await self.send_json({'type': 'connection.ready', 'session_id': self.session_id, 'user_id': self.user_id})

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name') and hasattr(self, 'user_id'):
            logger.info('webrtc.disconnected session_id=%s user_id=%s close_code=%s', self.session_id, self.user_id, close_code)
            await self.channel_layer.group_send(self.group_name, {'type': 'remote.event', 'event_type': 'peer.left', 'user_id': self.user_id, 'sender': self.channel_name})
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event_type = content.get('type')
        logger.info('webrtc.signal session_id=%s user_id=%s event=%s', self.session_id, self.user_id, event_type)
        if event_type in {'webrtc.offer', 'webrtc.answer', 'webrtc.ice-candidate'}:
            payload = content.get('payload')
            if not isinstance(payload, dict): return
            await self.channel_layer.group_send(self.group_name, {'type': 'remote.event', 'event_type': event_type, 'payload': payload, 'sender': self.channel_name})
        elif event_type == 'webrtc.renegotiate':
            await self.channel_layer.group_send(self.group_name, {'type': 'remote.event', 'event_type': event_type, 'sender': self.channel_name})
        elif event_type == 'chat.send':
            body = str(content.get('body', '')).strip()
            if not body or len(body) > 5000: await self.send_json({'type': 'chat.error', 'detail': 'متن پیام باید بین ۱ تا ۵۰۰۰ نویسه باشد'}); return
            message = await self.save_chat(body, str(content.get('client_id', ''))[:100])
            logger.info('chat.message session_id=%s user_id=%s message_id=%s', self.session_id, self.user_id, message.get('id'))
            await self.channel_layer.group_send(self.group_name, {'type': 'remote.event', 'event_type': 'chat.message', 'payload': message, 'sender': self.channel_name})

    async def remote_event(self, event):
        if event.get('event_type') in {'webrtc.offer', 'webrtc.answer', 'webrtc.ice-candidate', 'webrtc.renegotiate'} and event.get('sender') == self.channel_name: return
        await self.send_json({'type': event['event_type'], 'payload': event.get('payload', {}), 'peer_id': event.get('user_id')})

    @database_sync_to_async
    def authorized_session(self, user_id):
        if not user_id: return None
        session = RemoteSession.objects.select_related('requester', 'agent').filter(pk=self.session_id, status='active').first()
        if not session: return None
        if user_id in {session.requester_id, session.agent_id}: return session
        return None

    @database_sync_to_async
    def save_chat(self, body, client_id):
        from .permissions import role_for
        user = get_user_model().objects.get(pk=self.user_id)
        is_staff = role_for(user) in {'owner', 'admin', 'support'} or user.is_staff
        session = RemoteSession.objects.select_related('conversation').get(pk=self.session_id)
        conversation = session.conversation
        payload = {
            'client_id': client_id, 'sender': self.user_id, 'sender_name': self.user_name,
            'body': body, 'is_staff_reply': is_staff,
        }
        if not conversation:
            payload['id'] = f'local-{uuid.uuid4()}'
            return payload
        # پیام تکراری عمداً حذف نمی‌شود (کاربر می‌تواند دو بار «باشه» بفرستد)
        message = Message.objects.create(
            conversation=conversation, sender_id=self.user_id, body=body,
            is_staff_reply=is_staff, is_ai=False,
        )
        # وضعیت مکالمه/escalation/معیارهای پشتیبان هم به‌روز شود
        try:
            if is_staff and conversation.user_id != self.user_id:
                conversation.mark_agent_message(user)
            elif conversation.user_id == self.user_id:
                conversation.mark_user_message()
        except Exception:
            logger.exception('chat.conversation_update_failed conversation=%s', conversation.pk)
        payload['id'] = message.id
        payload['created_at'] = message.created_at.isoformat()
        return payload
