"""
Material Endpoints

File upload, folders management, and material CRUD.
"""

import os
import uuid as uuid_lib
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.deps import get_db, get_current_teacher
from app.core.config import settings
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    FileProcessingException,
)
from app.models.user import User
from app.models.material import Material, MaterialFolder
from app.schemas.material import (
    MaterialResponse,
    MaterialListResponse,
    MaterialUploadResponse,
    MaterialUpdate,
    MaterialFolderCreate,
    MaterialFolderUpdate,
    MaterialFolderResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter()


# ============== Materials ==============

@router.get("", response_model=MaterialListResponse)
async def get_materials(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=1000),
    folder_id: Optional[UUID] = Query(None, alias="folderId"),
    file_type: Optional[str] = Query(None, alias="fileType"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all materials for current teacher with pagination.
    Materials are stored independently and linked to projects during project creation.
    """
    query = select(Material).where(Material.teacher_id == current_user.id)
    
    # Apply filters
    if folder_id:
        query = query.where(Material.folder_id == folder_id)
    if file_type:
        query = query.where(Material.file_type == file_type)
    if search:
        query = query.where(Material.original_name.ilike(f"%{search}%"))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.order_by(Material.uploaded_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    materials = result.scalars().all()
    
    return MaterialListResponse(
        items=[
            MaterialResponse(
                id=m.id,
                folderId=m.folder_id,
                fileName=m.file_name,
                originalName=m.original_name,
                fileType=m.file_type,
                filePath=m.file_path,
                fileSize=m.file_size,
                uploadedAt=m.uploaded_at,
                openaiFileId=m.openai_file_id,
            )
            for m in materials
        ],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.post("/upload", response_model=MaterialUploadResponse)
async def upload_material(
    file: UploadFile = File(...),
    folder_id: Optional[UUID] = Form(None, alias="folderId"),
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a new material file.
    
    Files are stored in their original format and can later be
    linked to projects during project creation.
    
    Accepts: PDF, DOCX, DOC, TXT, PNG, JPG, JPEG
    Max size: 50MB
    """
    # Validate file extension
    file_ext = file.filename.split(".")[-1].lower() if file.filename else ""
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise FileProcessingException(
            message=f"Тип файла не поддерживается. Разрешены: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            filename=file.filename,
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise FileProcessingException(
            message=f"Файл слишком большой. Максимальный размер: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
            filename=file.filename,
        )
    
    # Generate unique filename
    unique_id = str(uuid_lib.uuid4())
    file_name = f"{unique_id}.{file_ext}"
    
    # Create upload directory if not exists
    upload_dir = os.path.join(settings.UPLOAD_DIR, "materials")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create database record (no project link - materials are linked later)
    material = Material(
        teacher_id=current_user.id,
        folder_id=folder_id,
        file_name=file_name,
        original_name=file.filename or "unknown",
        file_type=file_ext,
        file_path=f"/uploads/materials/{file_name}",
        file_size=file_size,
    )
    
    db.add(material)
    await db.commit()
    await db.refresh(material)
    
    return MaterialUploadResponse(
        id=material.id,
        fileName=material.original_name,
        fileType=material.file_type,
        fileSize=material.file_size,
        message="File uploaded successfully",
    )


@router.delete("/{material_id}", response_model=MessageResponse)
async def delete_material(
    material_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete material by ID.
    Also deletes file from OpenAI if uploaded there.
    """
    from app.services.openai_vectorstore import get_vectorstore_service
    
    query = select(Material).where(
        Material.id == material_id,
        Material.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    material = result.scalar_one_or_none()
    
    if not material:
        raise NotFoundException(resource="Material", resource_id=str(material_id))
    
    # Delete file from OpenAI if exists
    if material.openai_file_id:
        try:
            vs_service = get_vectorstore_service()
            vs_service.delete_file(material.openai_file_id)
        except Exception as e:
            print(f"Warning: Failed to delete file from OpenAI: {e}")
    
    # Delete file from disk (if exists)
    file_path = os.path.join(settings.UPLOAD_DIR, "materials", material.file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    await db.delete(material)
    await db.commit()
    
    return MessageResponse(message="Material deleted successfully")


@router.patch("/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: UUID,
    material_data: MaterialUpdate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Update material (e.g., move to folder).
    """
    query = select(Material).where(
        Material.id == material_id,
        Material.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    material = result.scalar_one_or_none()
    
    if not material:
        raise NotFoundException(resource="Material", resource_id=str(material_id))
    
    # Update folder_id (can be None to move to root)
    if material_data.folder_id is not None or 'folder_id' in material_data.model_dump(exclude_unset=True):
        # Verify folder exists and belongs to teacher (if not None)
        if material_data.folder_id:
            folder_query = select(MaterialFolder).where(
                MaterialFolder.id == material_data.folder_id,
                MaterialFolder.teacher_id == current_user.id,
            )
            folder_result = await db.execute(folder_query)
            folder = folder_result.scalar_one_or_none()
            if not folder:
                raise NotFoundException(resource="Folder", resource_id=str(material_data.folder_id))
        
        material.folder_id = material_data.folder_id
    
    await db.commit()
    await db.refresh(material)
    
    return MaterialResponse(
        id=material.id,
        folderId=material.folder_id,
        fileName=material.file_name,
        originalName=material.original_name,
        fileType=material.file_type,
        filePath=material.file_path,
        fileSize=material.file_size,
        uploadedAt=material.uploaded_at,
        openaiFileId=material.openai_file_id,
    )


# ============== Folders ==============

@router.get("/folders", response_model=list[MaterialFolderResponse])
async def get_folders(
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all folders for current teacher.
    """
    query = select(MaterialFolder).where(MaterialFolder.teacher_id == current_user.id)
    query = query.order_by(MaterialFolder.name)
    
    result = await db.execute(query)
    folders = result.scalars().all()
    
    response = []
    for folder in folders:
        # Count materials in folder
        count_query = select(func.count()).where(Material.folder_id == folder.id)
        count_result = await db.execute(count_query)
        materials_count = count_result.scalar() or 0
        
        response.append(
            MaterialFolderResponse(
                id=folder.id,
                teacherId=folder.teacher_id,
                name=folder.name,
                description=folder.description,
                materialsCount=materials_count,
                createdAt=folder.created_at,
            )
        )
    
    return response


@router.post("/folders", response_model=MaterialFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: MaterialFolderCreate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new folder.
    """
    folder = MaterialFolder(
        teacher_id=current_user.id,
        name=folder_data.name,
        description=folder_data.description,
    )
    
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    
    return MaterialFolderResponse(
        id=folder.id,
        teacherId=folder.teacher_id,
        name=folder.name,
        description=folder.description,
        materialsCount=0,
        createdAt=folder.created_at,
    )


@router.put("/folders/{folder_id}", response_model=MaterialFolderResponse)
async def update_folder(
    folder_id: UUID,
    folder_data: MaterialFolderUpdate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Update folder by ID.
    """
    query = select(MaterialFolder).where(
        MaterialFolder.id == folder_id,
        MaterialFolder.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise NotFoundException(resource="Folder", resource_id=str(folder_id))
    
    if folder_data.name is not None:
        folder.name = folder_data.name
    if folder_data.description is not None:
        folder.description = folder_data.description
    
    await db.commit()
    await db.refresh(folder)
    
    # Count materials
    count_query = select(func.count()).where(Material.folder_id == folder.id)
    count_result = await db.execute(count_query)
    materials_count = count_result.scalar() or 0
    
    return MaterialFolderResponse(
        id=folder.id,
        teacherId=folder.teacher_id,
        name=folder.name,
        description=folder.description,
        materialsCount=materials_count,
        createdAt=folder.created_at,
    )


@router.delete("/folders/{folder_id}", response_model=MessageResponse)
async def delete_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete folder by ID.
    Materials in the folder are not deleted, just unlinked.
    """
    query = select(MaterialFolder).where(
        MaterialFolder.id == folder_id,
        MaterialFolder.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise NotFoundException(resource="Folder", resource_id=str(folder_id))
    
    # Unlink materials from folder
    materials_query = select(Material).where(Material.folder_id == folder_id)
    materials_result = await db.execute(materials_query)
    for material in materials_result.scalars():
        material.folder_id = None
    
    await db.delete(folder)
    await db.commit()
    
    return MessageResponse(message="Folder deleted successfully")
