from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Project
from .serializers import ProjectSerializer
from workspaces.models import Workspace


class ProjectViewSet(viewsets.ModelViewSet):
    """CRUD operations for projects scoped to workspaces."""
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Project.objects.filter(owner=self.request.user)
        workspace_id = self.request.query_params.get('workspace') or self.request.headers.get('X-Workspace-Id')
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        return queryset

    def perform_create(self, serializer):
        workspace_id = (
            self.request.data.get('workspace')
            or self.request.query_params.get('workspace')
            or self.request.headers.get('X-Workspace-Id')
        )
        workspace = None
        if workspace_id:
            workspace = get_object_or_404(Workspace, id=workspace_id, owner=self.request.user)
        else:
            workspace = Workspace.objects.filter(owner=self.request.user).first()
            if not workspace:
                workspace = Workspace.objects.create(name="Default Client", owner=self.request.user)
        serializer.save(owner=self.request.user, workspace=workspace)

