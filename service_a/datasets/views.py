from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from .models import Dataset
from .serializers import DatasetSerializer


class DatasetViewSet(ModelViewSet):
    """Datasets, strictly scoped to the requesting user.

    Tenancy is enforced at the API layer, not just the database: every query is
    filtered to datasets the user created. A client cannot read another client's
    data by passing a different ``?workspace=`` id, and cannot create a dataset
    owned by someone else (``created_by`` is stamped server-side).

    ``get_object`` (used by retrieve/update/destroy) runs against this same
    filtered queryset, so a direct ``/datasets/{id}/`` for a dataset the user
    does not own returns 404 rather than leaking it.
    """

    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated]
    # Real access always flows through get_queryset; never expose .all().
    queryset = Dataset.objects.none()

    def get_queryset(self):
        qs = Dataset.objects.filter(created_by=self.request.user)
        workspace = self.request.query_params.get("workspace")
        if workspace:
            qs = qs.filter(workspace_id=workspace)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
