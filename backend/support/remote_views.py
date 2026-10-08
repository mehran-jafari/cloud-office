from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .permissions import CanReplySupport
from .models import Conversation
from .remote_models import RemoteSession
from .remote_serializers import RemoteSessionCreateSerializer, RemoteSessionJoinSerializer, RemoteSessionSerializer

class RemoteSessionCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = RemoteSessionCreateSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        conversation = None
        conversation_id = serializer.validated_data.get('conversation_id')
        if conversation_id:
            conversation = get_object_or_404(Conversation, pk=conversation_id, user=request.user)
        else:
            conversation = Conversation.objects.create(user=request.user, subject='جلسه اتصال امن')
        raw, digest = RemoteSession.create_code()
        session = RemoteSession.objects.create(requester=request.user, conversation=conversation, code_hash=digest, mode=serializer.validated_data['mode'], expires_at=timezone.now() + timedelta(minutes=10))
        data = RemoteSessionSerializer(session).data; data['code'] = raw; data['consent_required'] = True; data['expires_in_seconds'] = 600
        return Response(data, status=status.HTTP_201_CREATED)

class RemoteSessionJoinView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not CanReplySupport().has_permission(request, self): return Response({'detail': 'مجوز پشتیبانی از راه دور برای این کاربر فعال نشده است.'}, status=403)
        serializer = RemoteSessionJoinSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        session = get_object_or_404(RemoteSession, code_hash=RemoteSession.hash_code(serializer.validated_data['code']))
        if session.is_expired(): session.status = 'expired'; session.save(update_fields=['status', 'updated_at']); return Response({'detail': 'کد جلسه منقضی شده است.'}, status=410)
        if session.status != 'pending': return Response({'detail': 'این جلسه دیگر قابل اتصال نیست.'}, status=409)
        session.agent = request.user; session.save(update_fields=['agent', 'updated_at'])
        return Response(RemoteSessionSerializer(session).data)

class RemoteSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, request, pk):
        return get_object_or_404(RemoteSession, pk=pk)
    def allowed(self, request, session): return request.user.id in {session.requester_id, session.agent_id}
    def get(self, request, pk):
        session = self.get_object(request, pk)
        if not self.allowed(request, session): return Response({'detail': 'دسترسی به این جلسه مجاز نیست.'}, status=403)
        if session.is_expired(): session.status = 'expired'; session.save(update_fields=['status', 'updated_at'])
        return Response(RemoteSessionSerializer(session).data)

class RemoteSessionConsentView(RemoteSessionDetailView):
    def post(self, request, pk):
        session = self.get_object(request, pk)
        if request.user.id != session.requester_id: return Response({'detail': 'فقط صاحب سیستم می‌تواند رضایت بدهد.'}, status=403)
        if session.is_expired() or session.status != 'pending' or not session.agent_id: return Response({'detail': 'جلسه آماده تأیید نیست.'}, status=409)
        now = timezone.now(); session.status = 'active'; session.consented_at = now; session.started_at = now; session.save(update_fields=['status', 'consented_at', 'started_at', 'updated_at'])
        return Response(RemoteSessionSerializer(session).data)

class RemoteSessionEndView(RemoteSessionDetailView):
    def post(self, request, pk):
        session = self.get_object(request, pk)
        if not self.allowed(request, session): return Response({'detail': 'دسترسی به این جلسه مجاز نیست.'}, status=403)
        session.status = 'ended'; session.ended_at = timezone.now(); session.save(update_fields=['status', 'ended_at', 'updated_at'])
        return Response(RemoteSessionSerializer(session).data)
