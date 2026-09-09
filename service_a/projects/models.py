from django.db import models
from django.contrib.auth import get_user_model
from common.models import TimeStampedModel

from workspaces.models import Workspace

User = get_user_model()


class Project(TimeStampedModel):
    """A project owned by a user and scoped to a workspace (client)."""
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='projects', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

