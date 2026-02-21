from django.contrib.auth import authenticate, login, logout
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
