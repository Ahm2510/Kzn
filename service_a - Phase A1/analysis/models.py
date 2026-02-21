from django.db import models
from django.core.validators import FileExtensionValidator
from common.models import TimeStampedModel
from projects.models import Project


class AnalysisRun(TimeStampedModel):
    """Tracks an analysis run for a project. Calls service_b to generate insights."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='analysis_runs')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending')
    
    # File paths (stored on disk)
    current_file_path = models.CharField(max_length=512)
    baseline_file_path = models.CharField(max_length=512, null=True, blank=True)
    
    # Cleaning options (JSON)
    cleaning_options = models.JSONField(default=dict, blank=True)
    
    # Results from service_b
    insight_report = models.JSONField(null=True, blank=True)  # Stores the InsightReport JSON
    pdf_file_path = models.CharField(max_length=512, null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} - {self.status} - {self.created_at}"

