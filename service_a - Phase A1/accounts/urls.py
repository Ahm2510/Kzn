from django.urls import path
from .views import login_view, logout_view, me_view, get_csrf_token

urlpatterns = [
    path('auth/csrf/', get_csrf_token, name='csrf-token'),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/me/', me_view, name='me'),
]
