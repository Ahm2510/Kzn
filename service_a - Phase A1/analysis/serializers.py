from rest_framework import serializers
from .models import AnalysisRun


class AnalysisRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisRun
        fields = [
            'id', 'project', 'status', 'current_file_path', 'baseline_file_path',
            'cleaning_options', 'insight_report', 'pdf_file_path', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'insight_report', 'pdf_file_path', 'error_message',
            'created_at', 'updated_at'
        ]


class AnalysisRunCreateSerializer(serializers.Serializer):
    """Serializer for creating an analysis run."""
    project_id = serializers.IntegerField()
    current_file = serializers.FileField()
    baseline_file = serializers.FileField(required=False, allow_null=True)
    cleaning_options = serializers.JSONField(required=False, default=dict)
    metric_schema = serializers.CharField(required=False, allow_null=True, default=None)

