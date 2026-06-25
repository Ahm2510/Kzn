from django.db import models


class TimeStampedModel(models.Model):
    """Abstract model that provides created_at and updated_at timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class WorkspaceScopedModel(models.Model):
    """
    Abstract base that scopes a row to a tenant (workspace).

    Several apps (``datasets``, ``jobs``, ``pipelines``) already inherit from
    this and their initial migrations persist a ``workspace_id`` UUID column,
    but the base class itself was missing from ``common.models`` — importing it
    raised ImportError and prevented those apps from loading. Defining it here
    restores tenant isolation: every scoped record carries the UUID of the
    owning :class:`workspaces.models.Workspace`, so two distributor clients'
    data can never be queried together by accident.

    The field matches the shape already baked into the existing migrations
    (``workspace_id = UUIDField()``), so no schema change is required.
    """
    workspace_id = models.UUIDField()

    class Meta:
        abstract = True
