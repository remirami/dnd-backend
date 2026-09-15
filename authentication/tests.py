import re

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class AuthenticationSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.test_username = "paladin_arthas"
        self.test_email = "arthas@menethil.com"
        self.test_password = "HolyLightPassword!2024"
        self.user = User.objects.create_user(
            username=self.test_username,
            email=self.test_email,
            password=self.test_password,
            first_name="Arthas",
            last_name="Menethil"
        )

    def tearDown(self):
        cache.clear()

    def test_user_registration(self):
        """Test successful user registration sets HttpOnly refresh cookie and returns access token"""
        url = reverse('register')
        data = {
            "username": "jaina_proudmoore",
            "email": "jaina@dalaran.com",
            "password": "FrostMagePassword!2024",
            "password2": "FrostMagePassword!2024",
            "first_name": "Jaina",
            "last_name": "Proudmoore"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['refresh_token']['httponly'])
        self.assertTrue(User.objects.filter(username="jaina_proudmoore").exists())

    def test_user_registration_mismatched_passwords(self):
        """Test registration fails if passwords do not match"""
        url = reverse('register')
        data = {
            "username": "illidan_stormrage",
            "email": "illidan@blacktemple.com",
            "password": "PasswordOne!2024",
            "password2": "PasswordTwo!2024"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_user_registration_duplicate_username_or_email(self):
        """Test registration prevents duplicate usernames and emails (case-insensitive)"""
        url = reverse('register')
        # Duplicate username
        response = self.client.post(url, {
            "username": "PALADIN_ARTHAS",
            "email": "unique@example.com",
            "password": "Password!2024",
            "password2": "Password!2024"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Duplicate email
        response = self.client.post(url, {
            "username": "unique_hero",
            "email": "ARTHAS@MENETHIL.COM",
            "password": "Password!2024",
            "password2": "Password!2024"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_sets_httponly_cookie(self):
        """Test login returns access token in body and refresh token in HttpOnly cookie"""
        url = reverse('token_obtain_pair')
        response = self.client.post(url, {
            "username": self.test_username,
            "password": self.test_password
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['refresh_token']['httponly'])

    def test_cookie_token_refresh_and_rotation(self):
        """Test refreshing token using the HttpOnly cookie and verify rotation"""
        login_url = reverse('token_obtain_pair')
        login_res = self.client.post(login_url, {
            "username": self.test_username,
            "password": self.test_password
        }, format='json')
        initial_refresh_cookie = login_res.cookies['refresh_token'].value

        # Refresh token using cookie
        refresh_url = reverse('token_refresh')
        self.client.cookies['refresh_token'] = initial_refresh_cookie
        refresh_res = self.client.post(refresh_url, format='json')

        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_res.data)
        self.assertIn('refresh_token', refresh_res.cookies)
        new_refresh_cookie = refresh_res.cookies['refresh_token'].value
        self.assertNotEqual(initial_refresh_cookie, new_refresh_cookie)

    def test_logout_blacklists_refresh_token(self):
        """Test logout blacklists the refresh token and clears cookie"""
        login_url = reverse('token_obtain_pair')
        login_res = self.client.post(login_url, {
            "username": self.test_username,
            "password": self.test_password
        }, format='json')
        refresh_cookie = login_res.cookies['refresh_token'].value

        # Logout
        logout_url = reverse('logout')
        self.client.cookies['refresh_token'] = refresh_cookie
        logout_res = self.client.post(logout_url, format='json')
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Attempt to refresh using blacklisted token
        refresh_url = reverse('token_refresh')
        self.client.cookies['refresh_token'] = refresh_cookie
        failed_refresh = self.client.post(refresh_url, format='json')
        self.assertEqual(failed_refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_reset_flow(self):
        """Test full password reset cycle from request to email to confirmation"""
        reset_req_url = reverse('password_reset_request')
        response = self.client.post(reset_req_url, {"email": self.test_email}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        email_content = mail.outbox[0].body
        self.assertIn("reset-password?uid=", email_content)

        # Extract uid and token from email
        uid_match = re.search(r'uid=([^&\s]+)', email_content)
        token_match = re.search(r'token=([^&\s]+)', email_content)
        self.assertIsNotNone(uid_match)
        self.assertIsNotNone(token_match)
        uid = uid_match.group(1)
        token = token_match.group(1)

        # Confirm password reset
        new_password = "NewLichKingPassword!2025"
        reset_confirm_url = reverse('password_reset_confirm')
        confirm_res = self.client.post(reset_confirm_url, {
            "uidb64": uid,
            "token": token,
            "password": new_password,
            "password2": new_password
        }, format='json')
        self.assertEqual(confirm_res.status_code, status.HTTP_200_OK)

        # Verify old password fails
        login_url = reverse('token_obtain_pair')
        old_login = self.client.post(login_url, {
            "username": self.test_username,
            "password": self.test_password
        }, format='json')
        self.assertEqual(old_login.status_code, status.HTTP_401_UNAUTHORIZED)

        # Verify new password succeeds
        new_login = self.client.post(login_url, {
            "username": self.test_username,
            "password": new_password
        }, format='json')
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

    def test_password_reset_anti_enumeration(self):
        """Test requesting password reset for a non-existent email returns same generic message without sending email"""
        reset_req_url = reverse('password_reset_request')
        response = self.client.post(reset_req_url, {"email": "nobody@nowhere.com"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], "If an account with this email exists, a password reset link has been sent.")
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_revokes_outstanding_tokens(self):
        """Test confirming a password reset revokes all existing refresh tokens for that user"""
        login_url = reverse('token_obtain_pair')
        login_res = self.client.post(login_url, {
            "username": self.test_username,
            "password": self.test_password
        }, format='json')
        active_refresh_token = login_res.cookies['refresh_token'].value

        # Reset password
        reset_req_url = reverse('password_reset_request')
        self.client.post(reset_req_url, {"email": self.test_email}, format='json')
        email_content = mail.outbox[0].body
        uid = re.search(r'uid=([^&\s]+)', email_content).group(1)
        token = re.search(r'token=([^&\s]+)', email_content).group(1)

        reset_confirm_url = reverse('password_reset_confirm')
        new_pass = "FrostmournePassword!2025"
        self.client.post(reset_confirm_url, {
            "uidb64": uid,
            "token": token,
            "password": new_pass,
            "password2": new_pass
        }, format='json')

        # Previous refresh token should now be blacklisted
        refresh_url = reverse('token_refresh')
        self.client.cookies['refresh_token'] = active_refresh_token
        revoked_refresh_res = self.client.post(refresh_url, format='json')
        self.assertEqual(revoked_refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rate_limiting_on_login(self):
        """Test rate limiting triggers 429 Too Many Requests after 5 attempts within a minute"""
        login_url = reverse('token_obtain_pair')
        for _ in range(5):
            self.client.post(login_url, {
                "username": self.test_username,
                "password": "wrongpassword"
            }, format='json')

        # 6th attempt should be throttled
        throttled_res = self.client.post(login_url, {
            "username": self.test_username,
            "password": "wrongpassword"
        }, format='json')
        self.assertEqual(throttled_res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
