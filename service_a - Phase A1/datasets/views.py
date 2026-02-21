from django.shortcuts import render

# Create your views here.
from rest_framework.viewsets import ModelViewSet
from .models import Dataset
from .serializers import DatasetSerializer


class DatasetViewSet(ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer

    def get_queryset(self):
        return Dataset.objects.filter(
            workspace_id=self.request.query_params.get("workspace")
        )
