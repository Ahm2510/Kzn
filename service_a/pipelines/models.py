from django.db import models

# Create your models here.
from django.db import models
from common.models import TimeStampedModel, WorkspaceScopedModel

class Pipeline(TimeStampedModel, WorkspaceScopedModel):
    name = models.CharField(max_length=255)
    definition = models.JSONField()
    is_active = models.BooleanField(default=True)
