"""
User Schemas

Pydantic schemas for user-related requests and responses.
Compatible with frontend TypeScript types.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============== Base Schemas ==============

class UserBase(BaseModel):
    """Base user schema with common fields"""
    model_config = ConfigDict(populate_by_name=True)
    
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100, alias="firstName")
    last_name: str = Field(..., min_length=1, max_length=100, alias="lastName")
    role: str = Field(default="student", pattern="^(teacher|student)$")


# ============== Request Schemas ==============

class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login (OAuth2 compatible)"""
    username: EmailStr  # OAuth2 uses 'username' field
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    model_config = ConfigDict(populate_by_name=True)
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, alias="firstName")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, alias="lastName")


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


# ============== Response Schemas ==============

class UserResponse(BaseModel):
    """User response schema - matches frontend User type"""
    id: UUID
    email: str
    role: str
    firstName: Optional[str] = Field(None, validation_alias="first_name")
    lastName: Optional[str] = Field(None, validation_alias="last_name")
    createdAt: Optional[datetime] = Field(None, validation_alias="created_at")
    isVerified: Optional[bool] = Field(None, validation_alias="is_verified")

    class Config:
        from_attributes = True
        populate_by_name = True


class UserInDB(UserBase):
    """User schema with database fields (internal use)"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============== Auth Response Schemas ==============

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenWithRefresh(Token):
    """JWT tokens with refresh token"""
    refresh_token: str


class AuthResponse(BaseModel):
    """Authentication response with token and user"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request (legacy body-based — now cookie-based)"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Request to send a reset code to email"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Verify code and set new password"""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(..., min_length=6, max_length=100)


class EmailVerifyRequest(BaseModel):
    """Verify email with 6-digit code"""
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
