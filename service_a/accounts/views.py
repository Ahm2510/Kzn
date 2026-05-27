from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """Return CSRF token for frontend to use in subsequent requests."""
    return Response({'csrfToken': get_token(request)})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Authenticate user and create session."""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Email and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Django uses username for auth, but we accept email
    user = authenticate(request, username=email, password=password)
    
    if user is not None:
        login(request, user)
        return Response({
            'user': {
                'id': user.id,
                'email': user.email or user.username,
                'username': user.username,
                'is_staff': user.is_staff,
            },
            'csrfToken': get_token(request),
        })
    else:
        return Response(
            {'error': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Log out user and clear session."""
    logout(request)
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Return current authenticated user info."""
    user = request.user
    return Response({
        'user': {
            'id': user.id,
            'email': user.email or user.username,
            'username': user.username,
            'is_staff': user.is_staff,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    if not old_password or not new_password:
        return Response({'error': 'Both old and new passwords are required.'}, status=400)
    if not request.user.check_password(old_password):
        return Response({'error': 'Current password is incorrect.'}, status=400)
    if len(new_password) < 8:
        return Response({'error': 'New password must be at least 8 characters.'}, status=400)
    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)
    return Response({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_reset_user_password_view(request):
    if not request.user.is_staff:
        return Response({'error': 'Admin access required.'}, status=403)
    user_id = request.data.get('user_id')
    new_password = request.data.get('new_password')
    if not user_id or not new_password:
        return Response({'error': 'user_id and new_password are required.'}, status=400)
    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters.'}, status=400)
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)
    target_user.set_password(new_password)
    target_user.save()
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_users_view(request):
    if not request.user.is_staff:
        return Response({'error': 'Admin access required.'}, status=403)
    users = User.objects.all().values('id', 'username', 'email', 'is_staff', 'last_login')
    return Response(list(users))
