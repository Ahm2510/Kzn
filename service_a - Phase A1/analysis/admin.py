from django.contrib import admin
from .models import AnalysisRun


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('project__name',)
    readonly_fields = ('created_at', 'updated_at')

