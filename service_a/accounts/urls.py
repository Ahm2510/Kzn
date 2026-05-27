from django.urls import path
from .views import (
    login_view, logout_view, me_view, get_csrf_token,
    change_password_view, admin_reset_user_password_view, admin_list_users_view
)

urlpatterns = [
    path('auth/csrf/', get_csrf_token, name='csrf-token'),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/me/', me_view, name='me'),
    path('auth/change-password/', change_password_view, name='change-password'),
    path('auth/admin/reset-user-password/', admin_reset_user_password_view, name='admin-reset-password'),
    path('auth/admin/users/', admin_list_users_view, name='admin-users'),
]
