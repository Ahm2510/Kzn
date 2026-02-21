from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalysisRunViewSet

router = DefaultRouter()
router.register(r'analysis-runs', AnalysisRunViewSet, basename='analysis-run')

urlpatterns = router.urls

