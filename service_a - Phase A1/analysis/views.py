import base64
import logging
import os
import shutil
import threading
from pathlib import Path
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import AnalysisRun
from .serializers import AnalysisRunSerializer, AnalysisRunCreateSerializer
from projects.models import Project
from common.file_storage import save_uploaded_file, delete_file, get_upload_directory
from common.service_b_client import get_service_b_client

logger = logging.getLogger(__name__)


def _run_analysis_background(analysis_run_id, current_file_path, baseline_file_path,
                             cleaning_options, metric_schema, project_id):
    """Execute Service B analysis in a background thread (non-blocking)."""
    import django
    django.db.connections.close_all()

    try:
        analysis_run = AnalysisRun.objects.get(id=analysis_run_id)
        analysis_run.status = 'running'
        analysis_run.save()

        client = get_service_b_client()
        result = client.analyze(
            current_file_path=current_file_path,
            baseline_file_path=baseline_file_path,
            cleaning_options=cleaning_options,
            metric_schema=metric_schema,
        )

        # Save PDF from service_b response to service_a storage
        upload_dir = get_upload_directory() / str(project_id) / 'reports'
        upload_dir.mkdir(parents=True, exist_ok=True)
        pdf_filename = f"report_{analysis_run_id}.pdf"
        local_pdf_path = upload_dir / pdf_filename

        pdf_saved = False
        # Prefer base64-encoded PDF from response (works across services)
        pdf_base64 = result.get('pdf_base64')
        if pdf_base64:
            try:
                with open(str(local_pdf_path), 'wb') as f:
                    f.write(base64.b64decode(pdf_base64))
                pdf_saved = True
            except Exception:
                pass

        # Fallback: copy from shared filesystem (local dev only)
        if not pdf_saved:
            service_b_pdf_path = result.get('pdf_path')
            if service_b_pdf_path and os.path.exists(service_b_pdf_path):
                shutil.copy2(service_b_pdf_path, str(local_pdf_path))
                pdf_saved = True

        if pdf_saved:
            analysis_run.pdf_file_path = str(local_pdf_path.absolute())

        analysis_run.status = 'completed'
        analysis_run.insight_report = result.get('report')
        analysis_run.save()

    except Exception as e:
        logger.exception("Background analysis failed for run %s", analysis_run_id)
        try:
            analysis_run = AnalysisRun.objects.get(id=analysis_run_id)
            analysis_run.status = 'failed'
            analysis_run.error_message = str(e)
            analysis_run.save()
        except Exception:
            logger.exception("Failed to update analysis run %s after error", analysis_run_id)
    finally:
        try:
            analysis_run = AnalysisRun.objects.get(id=analysis_run_id)
            if analysis_run.status not in ['completed', 'failed']:
                analysis_run.status = 'failed'
                analysis_run.error_message = 'Unexpected termination'
                analysis_run.save(update_fields=['status', 'error_message'])
        except Exception:
            logger.exception("Final fallback failed for run %s", analysis_run_id)


class AnalysisRunViewSet(viewsets.ModelViewSet):
    """ViewSet for managing analysis runs."""
    serializer_class = AnalysisRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter by projects owned by the user
        return AnalysisRun.objects.filter(
            project__owner=self.request.user
        ).select_related('project')

    def get_serializer_class(self):
        if self.action == 'create':
            return AnalysisRunCreateSerializer
        return AnalysisRunSerializer

    def create(self, request, *args, **kwargs):
        """Create and trigger a new analysis run (non-blocking)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get project (validated by serializer)
        project_id = serializer.validated_data['project_id']
        project = get_object_or_404(Project, id=project_id, owner=request.user)
        
        # Save uploaded files
        current_file_path = save_uploaded_file(
            serializer.validated_data['current_file'],
            project.id
        )
        
        baseline_file_path = None
        if serializer.validated_data.get('baseline_file'):
            baseline_file_path = save_uploaded_file(
                serializer.validated_data['baseline_file'],
                project.id
            )
        
        # Get cleaning options and metric_schema
        cleaning_options = serializer.validated_data.get('cleaning_options', {})
        metric_schema = serializer.validated_data.get('metric_schema')
        
        # Create analysis run
        analysis_run = AnalysisRun.objects.create(
            project=project,
            status='pending',
            current_file_path=current_file_path,
            baseline_file_path=baseline_file_path,
            cleaning_options=cleaning_options,
        )
        
        # Dispatch analysis to background thread (non-blocking)
        thread = threading.Thread(
            target=_run_analysis_background,
            args=(analysis_run.id, current_file_path, baseline_file_path,
                  cleaning_options, metric_schema, project.id),
            daemon=True,
        )
        thread.start()
        
        return Response(
            AnalysisRunSerializer(analysis_run).data,
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Download the PDF report for an analysis run."""
        analysis_run = self.get_object()
        
        if not analysis_run.pdf_file_path or not os.path.exists(analysis_run.pdf_file_path):
            raise Http404("PDF report not found")
        
        return FileResponse(
            open(analysis_run.pdf_file_path, 'rb'),
            content_type='application/pdf',
            filename=f'analysis_report_{analysis_run.id}.pdf'
        )

