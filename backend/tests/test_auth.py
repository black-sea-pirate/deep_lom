"""
Authentication API Tests

Tests for user registration, login, and authentication flows.
"""

import pytest
from httpx import AsyncClient


class TestAuthRegister:
    """Tests for user registration endpoint."""
    
    @pytest.mark.asyncio
    async def test_register_teacher_success(self, client: AsyncClient):
        """Test successful teacher registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newteacher@test.com",
                "password": "securepassword123",
                "first_name": "New",
                "last_name": "Teacher",
                "role": "teacher",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newteacher@test.com"
        assert data["user"]["role"] == "teacher"
        assert "firstName" in data["user"]
        assert "lastName" in data["user"]
    
    @pytest.mark.asyncio
    async def test_register_student_success(self, client: AsyncClient):
        """Test successful student registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newstudent@test.com",
                "password": "securepassword123",
                "first_name": "New",
                "last_name": "Student",
                "role": "student",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "student"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_teacher):
        """Test registration with existing email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "teacher@test.com",  # Already exists
                "password": "securepassword123",
                "first_name": "Another",
                "last_name": "Teacher",
                "role": "teacher",
            },
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "securepassword123",
                "first_name": "Test",
                "last_name": "User",
                "role": "student",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with short password."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "123",  # Too short
                "first_name": "Test",
                "last_name": "User",
                "role": "student",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_invalid_role(self, client: AsyncClient):
        """Test registration with invalid role."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "securepassword123",
                "first_name": "Test",
                "last_name": "User",
                "role": "admin",  # Invalid role
            },
        )
        
        assert response.status_code == 422


class TestAuthLogin:
    """Tests for user login endpoint."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_teacher):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "teacher@test.com",
                "password": "testpassword123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "teacher@test.com"
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_teacher):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "teacher@test.com",
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent email."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@test.com",
                "password": "anypassword",
            },
        )
        
        assert response.status_code == 401


class TestAuthMe:
    """Tests for current user endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, teacher_headers, test_teacher):
        """Test getting current user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=teacher_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "teacher@test.com"
        assert data["role"] == "teacher"
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting current user without token."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        
        assert response.status_code == 401


class TestAuthLogout:
    """Tests for logout endpoint."""
    
    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, teacher_headers):
        """Test successful logout."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=teacher_headers,
        )
        
        assert response.status_code == 200
        assert "message" in response.json()


class TestChangePassword:
    """Tests for password change endpoint."""
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, teacher_headers):
        """Test successful password change."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=teacher_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, teacher_headers):
        """Test password change with wrong current password."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=teacher_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
            },
        )
        
        assert response.status_code == 400
