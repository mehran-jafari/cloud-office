"""دسترسی مالک یا اشتراک با فلگ‌های can_view / can_download / can_edit."""
from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from .models import File, FileShare


def get_file_for_user(user, pk, *, need_download=False, need_edit=False, need_view=True):
    obj = File.objects.filter(pk=pk).select_related('owner').first()
    if not obj:
        raise Http404
    if obj.owner_id == user.id:
        return obj, None
    share = (
        FileShare.objects.filter(file=obj, shared_with=user)
        .select_related('shared_by')
        .first()
    )
    if not share:
        raise Http404
    if need_view and not share.can_view:
        raise Http404
    if need_download and not share.can_download:
        raise PermissionDenied('اجازه دانلود/کپی این فایل را ندارید.')
    if need_edit and not share.can_edit:
        raise PermissionDenied('اجازه ویرایش این فایل را ندارید.')
    # انقضای اشتراک
    if share.expires_at:
        from django.utils import timezone
        if share.expires_at < timezone.now():
            raise PermissionDenied('این اشتراک منقضی شده است.')
    return obj, share
