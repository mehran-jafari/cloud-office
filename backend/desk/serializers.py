from rest_framework import serializers
from .models import AddressBookEntry, DeskConference, DeskSession, Device


class DevicePrivateSerializer(serializers.ModelSerializer):
    """هش رمز هرگز سریالایز نمی‌شود. رمز خام فقط پس از rotate توسط ویو به‌صورت دستی اضافه می‌شود."""

    class Meta:
        model = Device
        fields = [
            'desk_id', 'token', 'alias', 'hostname', 'os_name',
            'online', 'last_seen',
        ]


class DevicePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['desk_id', 'alias', 'hostname', 'os_name', 'online']


class AddressBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddressBookEntry
        fields = ['id', 'desk_id', 'alias', 'last_connected', 'created_at']


class DeskSessionSerializer(serializers.ModelSerializer):
    host_desk_id = serializers.CharField(source='host.desk_id', read_only=True)
    client_desk_id = serializers.CharField(source='client.desk_id', read_only=True)
    host_alias = serializers.CharField(source='host.alias', read_only=True)
    client_alias = serializers.CharField(source='client.alias', read_only=True)

    class Meta:
        model = DeskSession
        fields = [
            'session_key', 'status', 'started_at', 'ended_at',
            'host_desk_id', 'client_desk_id', 'host_alias', 'client_alias',
        ]


class DeskConferenceSerializer(serializers.ModelSerializer):
    host_desk_id = serializers.CharField(source='host.desk_id', read_only=True)

    class Meta:
        model = DeskConference
        fields = ['code', 'title', 'status', 'host_desk_id', 'created_at']
