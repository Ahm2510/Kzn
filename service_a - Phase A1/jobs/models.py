from django.db import models

# Create your models here.
from django.db import models
from common.models import TimeStampedModel, WorkspaceScopedModel

class Job(TimeStampedModel, WorkspaceScopedModel):
    job_type = models.CharField(max_length=64)
    status = models.CharField(max_length=32)
    payload = models.JSONField()
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
