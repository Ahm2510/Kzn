from django.db import models

# Create your models here.
from django.db import models
from common.models import TimeStampedModel, WorkspaceScopedModel
from django.contrib.auth import get_user_model

User = get_user_model()

class Dataset(TimeStampedModel, WorkspaceScopedModel):
    name = models.CharField(max_length=255)
    schema = models.JSONField()
    row_count = models.IntegerField()
    location = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
