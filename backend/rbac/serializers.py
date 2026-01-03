from rest_framework import serializers


class PolicySerializer(serializers.Serializer):
    sub = serializers.CharField(max_length=255)
    dom = serializers.CharField(max_length=255, required=False, allow_blank=True, default="*")
    obj = serializers.CharField(max_length=255)
    act = serializers.CharField(max_length=255)


class AssignmentSerializer(serializers.Serializer):
    user = serializers.CharField(max_length=255)
    role = serializers.CharField(max_length=255)
    dom = serializers.CharField(max_length=255, required=False, allow_blank=True, default="*")
