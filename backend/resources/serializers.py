from rest_framework import serializers

from .models import ResourceEntry, ResourceLink


class ResourceLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceLink
        fields = ('id', 'link_type', 'url', 'extraction_code', 'note', 'is_active', 'created_at')


class ResourceEntrySerializer(serializers.ModelSerializer):
    links = ResourceLinkSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ResourceEntry
        fields = (
            'id',
            'post',
            'title',
            'description',
            'created_by',
            'created_by_username',
            'status',
            'reviewed_by',
            'reviewed_at',
            'reject_reason',
            'created_at',
            'links',
        )
        read_only_fields = ('created_by',)

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request is not None else None
        if user and user.is_authenticated and getattr(user, 'is_staff', False):
            return attrs

        protected = {
            'status',
            'reviewed_by',
            'reviewed_at',
            'reject_reason',
        }
        if any(k in attrs for k in protected):
            raise serializers.ValidationError('Not allowed.')
        return attrs