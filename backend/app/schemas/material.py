"""
Material Schemas

Pydantic schemas for materials and folders.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# ============== Folder Schemas ==============

class MaterialFolderBase(BaseModel):
    """Base folder schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class MaterialFolderCreate(MaterialFolderBase):
    """Schema for creating folder"""
    pass


class MaterialFolderUpdate(BaseModel):
    """Schema for updating folder"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class MaterialFolderResponse(MaterialFolderBase):
    """Folder response schema - matches frontend MaterialFolder"""
    id: UUID
    teacher_id: UUID = Field(alias="teacherId")
    materials_count: int = Field(alias="materialsCount")
    created_at: datetime = Field(alias="createdAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ============== Material Schemas ==============

class MaterialBase(BaseModel):
    """Base material schema"""
    file_name: str = Field(alias="fileName")
    file_type: str = Field(alias="fileType")


class MaterialResponse(MaterialBase):
    """Material response schema - matches frontend Material"""
    id: UUID
    folder_id: Optional[UUID] = Field(None, alias="folderId")
    file_path: str = Field(alias="filePath")
    file_size: int = Field(alias="fileSize")
    original_name: str = Field(alias="originalName")
    uploaded_at: datetime = Field(alias="uploadedAt")
    openai_file_id: Optional[str] = Field(None, alias="openaiFileId")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class MaterialListResponse(BaseModel):
    """Paginated material list response"""
    items: List[MaterialResponse]
    total: int
    page: int
    size: int
    pages: int


class MaterialUploadResponse(BaseModel):
    """Response after file upload"""
    id: UUID
    file_name: str = Field(alias="fileName")
    file_type: str = Field(alias="fileType")
    file_size: int = Field(alias="fileSize")
    message: str = "File uploaded successfully"
    
    class Config:
        populate_by_name = True


class MaterialUpdate(BaseModel):
    """Schema for updating material (e.g., moving to folder)"""
    folder_id: Optional[UUID] = Field(None, alias="folderId")
    
    class Config:
        populate_by_name = True
