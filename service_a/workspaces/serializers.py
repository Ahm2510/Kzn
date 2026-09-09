from rest_framework import serializers
from .models import Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ("id", "name", "owner", "firm_name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at", "owner")
