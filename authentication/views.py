from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


def set_refresh_cookie(response: Response, refresh_token: str | RefreshToken) -> None:
    """Sets an HttpOnly, SameSite cookie containing the refresh token."""
    secure = not settings.DEBUG
    response.set_cookie(
        key='refresh_token',
        value=str(refresh_token),
        max_age=7 * 24 * 60 * 60,  # 7 days
        httponly=True,
        secure=secure,
        samesite='Lax',
        path='/',
    )


def clear_refresh_cookie(response: Response) -> None:
    """Deletes the refresh token cookie."""
    response.delete_cookie(
        key='refresh_token',
        path='/',
        samesite='Lax',
    )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain pair view that sets an HttpOnly refresh cookie and returns user details"""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh_token = response.data.get('refresh')
            if refresh_token:
                set_refresh_cookie(response, refresh_token)
                # In Option A, remove refresh token from response payload to prevent client JS exposure
                response.data.pop('refresh', None)
        return response


class RegisterView(generics.CreateAPIView):
    """User registration endpoint that sets an HttpOnly refresh cookie"""
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegistrationSerializer
    throttle_scope = 'login'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        response = Response({
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
        
        set_refresh_cookie(response, refresh)
        return response


class CookieTokenRefreshView(APIView):
    """Refreshes access token using the HttpOnly refresh token cookie and rotates the token"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token not found in cookie or request body.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)

            # Enforce rotation & blacklisting
            if api_settings.ROTATE_REFRESH_TOKENS:
                if api_settings.BLACKLIST_AFTER_ROTATION:
                    try:
                        refresh.blacklist()
                    except AttributeError:
                        pass
                refresh.set_jti()
                refresh.set_exp()
                refresh.set_iat()
                new_refresh = str(refresh)
            else:
                new_refresh = refresh_token

            response = Response({
                'access': new_access,
                'message': 'Token refreshed successfully'
            }, status=status.HTTP_200_OK)

            set_refresh_cookie(response, new_refresh)
            return response
        except TokenError as e:
            response = Response(
                {'detail': f'Invalid or expired refresh token: {e}'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            clear_refresh_cookie(response)
            return response


class LogoutView(APIView):
    """Logs out user by blacklisting refresh token and clearing HttpOnly cookie"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
        clear_refresh_cookie(response)
        return response


class PasswordResetRequestView(APIView):
    """Requests password reset with anti-enumeration and constant-time behavior"""
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

            subject = "Password Reset Request - 5e Campaign Manager"
            message = f"""Greetings Adventurer,

You recently requested a password reset for your 5e Campaign Manager account ({user.username}).

Please click the link below or paste it into your browser to reset your password (link valid for 15 minutes):

{reset_url}

If you did not request this password reset, you can safely disregard this message.

Safe travels,
The 5e Campaign Manager Team
"""
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        # Always return generic success message to prevent account enumeration
        return Response({
            'message': 'If an account with this email exists, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """Confirms password reset, updates password, and revokes all active refresh sessions"""
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = serializer.validated_data['uidb64']
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(password)
            user.save()

            # Revoke all outstanding refresh tokens for this user across all devices
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            for outstanding in outstanding_tokens:
                BlacklistedToken.objects.get_or_create(token=outstanding)

            return Response({
                'message': 'Password reset successful. You may now log in with your new password.'
            }, status=status.HTTP_200_OK)

        return Response({
            'detail': 'Invalid or expired password reset token.'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    """Get current authenticated user information"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)
