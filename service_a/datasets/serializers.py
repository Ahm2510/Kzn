from rest_framework import serializers
from .models import Dataset


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = "__all__"
        # created_by is stamped from the authenticated user in the view, never
        # accepted from the client — a client must not be able to assign
        # ownership of a dataset to another user.
        read_only_fields = ("id", "created_at", "created_by")
