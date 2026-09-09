from django.db import migrations


def populate_project_workspaces(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    Workspace = apps.get_model('workspaces', 'Workspace')

    # Find projects with no workspace
    unassigned_projects = Project.objects.filter(workspace__isnull=True)
    if not unassigned_projects.exists():
        return

    # Map each owner to a default workspace
    workspace_cache = {}
    for project in unassigned_projects:
        owner = project.owner
        if owner.id not in workspace_cache:
            existing_ws = Workspace.objects.filter(owner=owner).first()
            if not existing_ws:
                existing_ws = Workspace.objects.create(
                    name="Default Client",
                    owner=owner
                )
            workspace_cache[owner.id] = existing_ws
        project.workspace = workspace_cache[owner.id]
        project.save(update_fields=['workspace'])


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_project_workspace'),
    ]

    operations = [
        migrations.RunPython(populate_project_workspaces, reverse_code=reverse_populate),
    ]
