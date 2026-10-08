from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from files.models import File
from support.permissions import has_perm, role_for

from . import services
from .models import AIUsageLog
from .provider import has_remote


class AIThrottle(ScopedRateThrottle):
    scope = 'ai'


class AIStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        quota = services.get_or_create_quota(request.user)
        return Response({
            'provider_configured': has_remote(),
            'monthly_tokens': quota.monthly_tokens,
            'used_tokens': quota.used_tokens,
            'remaining_tokens': quota.remaining(),
            'features': {
                'draft_mail': True,
                'summarize': True,
                'support_reply': True,
                'stt': True,
                'semantic_search': True,
                'meeting_summary': True,
            },
        })


class AIDraftMailView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        subject = str(request.data.get('subject') or '').strip()
        notes = str(request.data.get('notes') or request.data.get('body') or '').strip()
        tone = str(request.data.get('tone') or 'formal')
        recipient_name = str(request.data.get('recipient_name') or '').strip()
        if not notes:
            return Response({'detail': 'نکات نامه الزامی است'}, status=400)
        try:
            return Response(services.draft_mail(
                request.user, subject or 'بدون موضوع', notes, tone, recipient_name=recipient_name
            ))
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class AISummarizeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        text = str(request.data.get('text') or '').strip()
        purpose = str(request.data.get('purpose') or 'general')
        if len(text) < 10:
            return Response({'detail': 'متن برای خلاصه خیلی کوتاه است'}, status=400)
        try:
            return Response(services.summarize_text(request.user, text, purpose))
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class AISupportReplyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        if not (has_perm(request.user, 'reply_support') or role_for(request.user) in {'owner', 'admin', 'support'}):
            return Response({'detail': 'فقط کارشناس پشتیبانی'}, status=403)
        text = str(request.data.get('conversation') or request.data.get('text') or '').strip()
        if len(text) < 5:
            return Response({'detail': 'متن گفتگو الزامی است'}, status=400)
        try:
            return Response(services.suggest_support_reply(request.user, text))
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class AISpeechToTextView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        f = request.FILES.get('audio') or request.FILES.get('file')
        if not f:
            return Response({'detail': 'فایل صوتی الزامی است'}, status=400)
        if f.size > 25 * 1024 * 1024:
            return Response({'detail': 'حداکثر ۲۵ مگابایت'}, status=400)
        try:
            data = services.speech_to_text(request.user, f.read(), f.name)
            return Response(data)
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class AIMeetingSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        transcript = str(request.data.get('transcript') or '').strip()
        title = str(request.data.get('title') or 'جلسه').strip()
        if len(transcript) < 20:
            return Response({'detail': 'رونوشت جلسه خیلی کوتاه است'}, status=400)
        try:
            return Response(services.meeting_summary(request.user, transcript, title))
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class AIIndexFileView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        file_id = request.data.get('file_id')
        text = str(request.data.get('text') or '').strip()
        try:
            file_obj = File.objects.get(pk=file_id, owner=request.user)
        except File.DoesNotExist:
            return Response({'detail': 'فایل پیدا نشد'}, status=404)
        try:
            return Response(services.index_file_text(request.user, file_obj, text))
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class AISemanticSearchView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        query = str(request.data.get('query') or '').strip()
        if len(query) < 2:
            return Response({'detail': 'عبارت جست‌وجو الزامی است'}, status=400)
        try:
            return Response(services.semantic_search(request.user, query, int(request.data.get('limit') or 10)))
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)




class AICreateFileView(APIView):
    """تولید محتوا و ذخیره به‌صورت فایل متنی در فضای کاربر."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        title = str(request.data.get('title') or 'سند جدید').strip()[:200]
        prompt = str(request.data.get('prompt') or request.data.get('notes') or '').strip()
        doc_type = str(request.data.get('doc_type') or 'txt').strip()
        save = bool(request.data.get('save', True))
        if len(prompt) < 3:
            return Response({'detail': 'توضیح محتوا الزامی است'}, status=400)
        try:
            generated = services.create_document_content(request.user, title, prompt, doc_type)
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)

        if not save:
            return Response(generated)

        # ذخیره فایل
        import uuid
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from django.db.models import Sum
        from accounts.models import StorageQuota
        from files.models import File
        from files.workspace import log_activity

        ext = 'md' if doc_type in {'md', 'report', 'memo'} else 'txt'
        safe_name = f"{title[:80]}.{ext}".replace('/', '-').replace('\\', '-')
        content_bytes = generated['content'].encode('utf-8')
        size = len(content_bytes)
        quota, _ = StorageQuota.objects.get_or_create(user=request.user)
        used = File.objects.filter(owner=request.user).aggregate(total=Sum('size_bytes')).get('total') or 0
        if used + size > quota.allocated_bytes:
            return Response({'detail': 'سهمیه فضای ذخیره‌سازی کافی نیست', **generated}, status=400)

        storage_key = default_storage.save(
            f"uploads/{request.user.id}/{uuid.uuid4().hex}_{safe_name}",
            ContentFile(content_bytes),
        )
        obj = File.objects.create(
            name=safe_name,
            owner=request.user,
            storage_key=storage_key,
            mime_type='text/markdown' if ext == 'md' else 'text/plain',
            size_bytes=size,
        )
        log_activity(request.user, 'upload', f'ایجاد فایل با AI «{obj.name}»', target_type='file', target_id=obj.id)
        try:
            services.index_file_text(request.user, obj, generated['content'])
        except Exception:
            pass

        from files.serializers import FileSerializer
        return Response({
            **generated,
            'file': FileSerializer(obj, context={'request': request}).data,
            'saved': True,
        }, status=201)

class AIProofreadView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        text = str(request.data.get('text') or '').strip()
        if len(text) < 2:
            return Response({'detail': 'متن خالی است'}, status=400)
        try:
            return Response(services.proofread_text(request.user, text))
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class AIConferenceDocView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]
    throttle_scope = 'ai'

    def post(self, request):
        transcript = str(request.data.get('transcript') or '').strip()
        doc_kind = str(request.data.get('doc_kind') or 'minutes')
        title = str(request.data.get('title') or 'جلسه').strip()
        if len(transcript) < 15:
            return Response({'detail': 'رونوشت جلسه خیلی کوتاه است'}, status=400)
        try:
            return Response(services.conference_document(request.user, transcript, doc_kind, title))
        except PermissionError as e:
            return Response({'detail': str(e)}, status=429)
        except Exception as e:
            return Response({'detail': str(e)}, status=502)


class AIUsageLogView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AIUsageLog.objects.filter(user=request.user)[:50]
        return Response([
            {
                'id': x.id,
                'action': x.action,
                'tokens_used': x.tokens_used,
                'model_name': x.model_name,
                'success': x.success,
                'detail': x.detail,
                'created_at': x.created_at.isoformat(),
            }
            for x in qs
        ])
