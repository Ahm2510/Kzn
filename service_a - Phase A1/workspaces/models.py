from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model
from common.models import TimeStampedModel

User = get_user_model()

class Workspace(TimeStampedModel):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
