from django.shortcuts import render

# Create your views here.
from rest_framework.viewsets import ModelViewSet
from .models import Pipeline
from .serializers import PipelineSerializer


class PipelineViewSet(ModelViewSet):
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def get_queryset(self):
        return Pipeline.objects.filter(
            workspace_id=self.request.query_params.get("workspace")
        )
