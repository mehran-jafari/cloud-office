from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import ActivityLog, Correspondence, File, FileShare, Folder, PublicShareLink

User = get_user_model()

COLOR_MAP = {
    'sheet': '#35b982',
    'doc': '#3489f5',
    'pdf': '#e05a5a',
    'folder': '#7667f7',
    'image': '#f4af46',
    'other': '#93a0b5',
}


def human_size(num: int) -> str:
    if num < 1024:
        return f'{num} بایت'
    if num < 1024 ** 2:
        return f'{num / 1024:.1f} کیلوبایت'
    if num < 1024 ** 3:
        return f'{num / 1024 ** 2:.1f} مگابایت'
    return f'{num / 1024 ** 3:.2f} گیگابایت'


def detect_type(name: str, mime: str = '') -> str:
    lower = (name or '').lower()
    if mime == 'inode/directory':
        return 'folder'
    if lower.endswith(('.xlsx', '.xls', '.ods', '.csv')):
        return 'sheet'
    if lower.endswith(('.docx', '.doc', '.odt', '.rtf', '.txt')):
        return 'doc'
    if lower.endswith('.pdf'):
        return 'pdf'
    if lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
        return 'image'
    return 'other'


class FolderSerializer(serializers.ModelSerializer):
    def validate_parent(self, parent):
        request = self.context.get('request')
        if parent and request and parent.owner_id != request.user.id:
            raise serializers.ValidationError('پوشه والد متعلق به این کاربر نیست.')
        return parent

    class Meta:
        model = Folder
        fields = ['id', 'name', 'parent', 'created_at']


class FileSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    updated = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = [
            'id', 'name', 'type', 'size', 'updated', 'owner', 'color',
            'folder', 'mime_type', 'size_bytes', 'current_version', 'is_deleted', 'deleted_at',
        ]
        read_only_fields = ['owner', 'current_version', 'mime_type', 'size_bytes']

    def validate_folder(self, folder):
        request = self.context.get('request')
        if folder and request and folder.owner_id != request.user.id:
            raise serializers.ValidationError('پوشه متعلق به این کاربر نیست.')
        return folder

    def get_type(self, obj):
        return detect_type(obj.name, obj.mime_type)

    def get_size(self, obj):
        return human_size(obj.size_bytes or 0)

    def get_updated(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at else ''

    def get_owner(self, obj):
        return obj.owner.get_full_name() or obj.owner.username

    def get_color(self, obj):
        return COLOR_MAP.get(detect_type(obj.name, obj.mime_type), COLOR_MAP['other'])


class FileShareSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file.name', read_only=True)
    file_id = serializers.IntegerField(source='file.id', read_only=True)
    shared_with_username = serializers.CharField(source='shared_with.username', read_only=True)
    shared_by_username = serializers.CharField(source='shared_by.username', read_only=True)
    permission_label = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    file_color = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = FileShare
        fields = [
            'id', 'file', 'file_id', 'file_name', 'file_type', 'file_size', 'file_color',
            'shared_with', 'shared_with_username', 'shared_by', 'shared_by_username',
            'permission', 'permission_label', 'can_view', 'can_download', 'can_edit', 'can_reshare',
            'capabilities', 'is_owner', 'message', 'expires_at', 'created_at',
        ]
        read_only_fields = ['shared_by', 'created_at', 'can_view', 'can_download', 'can_edit', 'can_reshare']

    def get_permission_label(self, obj):
        return dict(FileShare.PERMISSION_CHOICES).get(obj.permission, obj.permission)

    def get_file_type(self, obj):
        return detect_type(obj.file.name, obj.file.mime_type)

    def get_file_size(self, obj):
        return human_size(obj.file.size_bytes or 0)

    def get_file_color(self, obj):
        return COLOR_MAP.get(detect_type(obj.file.name, obj.file.mime_type), COLOR_MAP['other'])

    def get_capabilities(self, obj):
        return obj.capabilities()

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.file.owner_id == request.user.id

    def validate(self, attrs):
        request = self.context.get('request')
        file_obj = attrs.get('file') or getattr(self.instance, 'file', None)
        shared_with = attrs.get('shared_with')
        if file_obj and request:
            if file_obj.owner_id == request.user.id:
                pass  # owner always ok
            else:
                # reshare only if has can_reshare on an existing share
                share = FileShare.objects.filter(file=file_obj, shared_with=request.user, can_reshare=True).first()
                if not share:
                    raise serializers.ValidationError({'file': 'اجازه اشتراک‌گذاری مجدد این فایل را ندارید.'})
        if shared_with and request and shared_with.id == request.user.id:
            raise serializers.ValidationError({'shared_with': 'نمی‌توانید فایل را با خودتان به اشتراک بگذارید.'})
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        validated_data['shared_by'] = request.user
        share = FileShare(**validated_data)
        data = self.initial_data if hasattr(self, 'initial_data') else {}
        # اگر فلگ صریح آمده همان مبنا است؛ در غیر این صورت از سطح permission
        if any(k in data for k in ('can_download', 'can_edit', 'can_reshare', 'can_view')):
            share.can_view = True  # حداقل مشاهده برای اشتراک
            share.can_download = self._as_bool(data.get('can_download', False))
            share.can_edit = self._as_bool(data.get('can_edit', False))
            share.can_reshare = self._as_bool(data.get('can_reshare', False))
            # وابستگی منطقی
            if share.can_reshare:
                share.can_edit = True
                share.can_download = True
            elif share.can_edit:
                share.can_download = True
            if share.can_reshare:
                share.permission = 'full'
            elif share.can_edit:
                share.permission = 'edit'
            elif share.can_download:
                share.permission = 'download'
            else:
                share.permission = 'view'
        else:
            share.apply_permission_level()
        share.save()
        return share

    @staticmethod
    def _as_bool(value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    action_label = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'username', 'action', 'action_label', 'title', 'detail', 'target_type', 'target_id', 'created_at']
        read_only_fields = fields

    def get_action_label(self, obj):
        return dict(ActivityLog.ACTION_CHOICES).get(obj.action, obj.action)


class CorrespondenceSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    recipient_name = serializers.SerializerMethodField()
    priority_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = Correspondence
        fields = [
            'id', 'subject', 'body', 'sender', 'sender_name', 'recipient', 'recipient_name',
            'status', 'status_label', 'priority', 'priority_label', 'is_read', 'parent',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['sender', 'status', 'is_read', 'created_at', 'updated_at']

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username

    def get_recipient_name(self, obj):
        return obj.recipient.get_full_name() or obj.recipient.username

    def get_priority_label(self, obj):
        return dict(Correspondence.PRIORITY_CHOICES).get(obj.priority, obj.priority)

    def get_status_label(self, obj):
        return dict(Correspondence.STATUS_CHOICES).get(obj.status, obj.status)


class UserLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class PublicShareLinkSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file.name', read_only=True)
    file_id = serializers.IntegerField(source='file.id', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    is_expired = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = PublicShareLink
        fields = [
            'id', 'file', 'file_id', 'file_name', 'token', 'permission',
            'expires_at', 'max_downloads', 'download_count', 'is_active',
            'note', 'created_at', 'created_by', 'created_by_username',
            'is_expired', 'public_url', 'has_password',
        ]
        read_only_fields = ['token', 'download_count', 'created_by', 'created_at']

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_has_password(self, obj):
        return bool(obj.password_hash)

    def get_public_url(self, obj):
        from django.conf import settings
        base = getattr(settings, 'PUBLIC_APP_URL', '').rstrip('/')
        if base:
            return f"{base}/public/share/{obj.token}"
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f"/public/share/{obj.token}")
        return f"/public/share/{obj.token}"
