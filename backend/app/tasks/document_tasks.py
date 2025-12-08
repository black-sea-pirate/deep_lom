"""
Document Processing Tasks

Celery tasks for document vectorization using OpenAI Vector Stores.

Unlike local ChromaDB approach, this:
1. Uploads files directly to OpenAI Files API
2. Creates Vector Store per project
3. Attaches files to Vector Store
4. OpenAI handles parsing, chunking, embedding - no local processing!

Uses synchronous database sessions to avoid asyncio event loop conflicts in Celery.
"""

import os
from sqlalchemy import update, select, func
from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import sync_session_maker
from app.services.openai_vectorstore import get_vectorstore_service


@celery_app.task(bind=True, name="vectorize_project_materials")
def vectorize_project_materials(self, project_id: str, material_ids: list[str]):
    """
    Vectorize all materials for a project using OpenAI Vector Store.
    
    This task:
    1. Creates Vector Store in OpenAI for this project
    2. For each material:
       - Uploads file to OpenAI Files API (if not already uploaded)
       - Attaches file to Vector Store
       - OpenAI automatically processes, chunks, embeds
    3. Waits for indexing completion
    4. Updates project vectorization status
    
    Args:
        project_id: UUID of the project
        material_ids: List of material UUIDs to process
    """
    from app.models.project import Project
    from app.models.material import Material, project_materials
    
    with sync_session_maker() as db:
        try:
            # Get project
            result = db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Initialize Vector Store service
            vs_service = get_vectorstore_service()
            
            # Create or reuse Vector Store for this project
            if not project.openai_vector_store_id:
                vector_store_id = vs_service.create_vector_store(
                    name=project.title,
                    project_id=str(project_id),
                )
                project.openai_vector_store_id = vector_store_id
                db.commit()
            else:
                vector_store_id = project.openai_vector_store_id
            
            # Process each material
            total = len(material_ids)
            
            for idx, material_id in enumerate(material_ids):
                try:
                    # Update progress
                    progress = int((idx / total) * 100)
                    project.vectorization_progress = progress
                    db.commit()
                    
                    # Mark material as processing
                    db.execute(
                        update(project_materials).where(
                            project_materials.c.project_id == project_id,
                            project_materials.c.material_id == material_id,
                        ).values(is_vectorized=1)  # processing
                    )
                    db.commit()
                    
                    # Get material
                    mat_result = db.execute(
                        select(Material).where(Material.id == material_id)
                    )
                    material = mat_result.scalar_one_or_none()
                    
                    if not material:
                        continue
                    
                    # Upload to OpenAI if not already uploaded
                    if not material.openai_file_id:
                        # Get local file path
                        file_path = os.path.join(
                            settings.UPLOAD_DIR, "materials", material.file_name
                        )
                        
                        if not os.path.exists(file_path):
                            # Mark as error
                            db.execute(
                                update(project_materials).where(
                                    project_materials.c.project_id == project_id,
                                    project_materials.c.material_id == material_id,
                                ).values(is_vectorized=-1)  # error
                            )
                            db.commit()
                            continue
                        
                        # Upload file to OpenAI
                        openai_file_id = vs_service.upload_file(
                            file_path=file_path,
                            filename=material.original_name,
                        )
                        
                        # Save OpenAI file ID to material
                        material.openai_file_id = openai_file_id
                        db.commit()
                        
                        # Optional: delete local file after upload
                        # os.remove(file_path)
                    
                    # Add file to Vector Store
                    # This triggers OpenAI's automatic parsing, chunking, embedding
                    vs_service.add_file_to_vector_store(
                        vector_store_id=vector_store_id,
                        file_id=material.openai_file_id,
                        wait_for_completion=True,
                        timeout=300,  # 5 minutes per file
                    )
                    
                    # Mark as done
                    db.execute(
                        update(project_materials).where(
                            project_materials.c.project_id == project_id,
                            project_materials.c.material_id == material_id,
                        ).values(is_vectorized=2)  # done
                    )
                    db.commit()
                    
                except Exception as e:
                    # Mark as error
                    db.execute(
                        update(project_materials).where(
                            project_materials.c.project_id == project_id,
                            project_materials.c.material_id == material_id,
                        ).values(is_vectorized=-1)  # error
                    )
                    db.commit()
                    import traceback
                    print(f"Error processing material {material_id}: {e}")
                    print(f"Traceback: {traceback.format_exc()}")
            
            # Check if any materials failed
            failed_count = db.execute(
                select(func.count()).select_from(project_materials).where(
                    project_materials.c.project_id == project_id,
                    project_materials.c.is_vectorized == -1,
                )
            ).scalar()
            
            if failed_count > 0:
                # Some materials failed - set partial status
                project.vectorization_status = "partial"
                project.status = "error"
                db.commit()
                return {
                    "status": "partial",
                    "project_id": project_id,
                    "materials_processed": total,
                    "materials_failed": failed_count,
                    "vector_store_id": vector_store_id,
                    "error": f"{failed_count} materials failed to index",
                }
            
            # Update project status
            project.vectorization_status = "completed"
            project.vectorization_progress = 100
            project.status = "ready"
            db.commit()
            
            return {
                "status": "success",
                "project_id": project_id,
                "materials_processed": total,
                "vector_store_id": vector_store_id,
            }
            
        except Exception as e:
            # Update project with error
            result = db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project:
                project.vectorization_status = "failed"
                project.vectorization_error = str(e)
                project.status = "draft"
                db.commit()
            raise


@celery_app.task(bind=True, name="upload_material_to_openai")
def upload_material_to_openai(self, material_id: str):
    """
    Upload a single material to OpenAI Files API.
    
    This can be used for pre-uploading materials before vectorization,
    so the vectorization step is faster.
    
    Args:
        material_id: UUID of the material in database
    """
    from app.models.material import Material
    
    with sync_session_maker() as db:
        try:
            # Get material
            result = db.execute(
                select(Material).where(Material.id == material_id)
            )
            material = result.scalar_one_or_none()
            
            if not material:
                raise ValueError(f"Material {material_id} not found")
            
            if material.openai_file_id:
                # Already uploaded
                return {
                    "status": "already_uploaded",
                    "material_id": material_id,
                    "openai_file_id": material.openai_file_id,
                }
            
            # Get file path
            file_path = os.path.join(
                settings.UPLOAD_DIR, "materials", material.file_name
            )
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Upload to OpenAI
            vs_service = get_vectorstore_service()
            openai_file_id = vs_service.upload_file(
                file_path=file_path,
                filename=material.original_name,
            )
            
            # Update material
            material.openai_file_id = openai_file_id
            db.commit()
            
            return {
                "status": "success",
                "material_id": material_id,
                "openai_file_id": openai_file_id,
            }
            
        except Exception as e:
            print(f"Error uploading material {material_id}: {e}")
            raise


@celery_app.task(bind=True, name="delete_openai_file")
def delete_openai_file(self, file_id: str):
    """
    Delete a file from OpenAI.
    
    Args:
        file_id: OpenAI file ID to delete
    """
    try:
        vs_service = get_vectorstore_service()
        success = vs_service.delete_file(file_id)
        
        return {
            "status": "success" if success else "failed",
            "file_id": file_id,
        }
        
    except Exception as e:
        print(f"Error deleting file {file_id}: {e}")
        raise


@celery_app.task(bind=True, name="delete_project_vector_store")
def delete_project_vector_store(self, vector_store_id: str):
    """
    Delete entire project Vector Store from OpenAI.
    
    Args:
        vector_store_id: OpenAI Vector Store ID to delete
    """
    try:
        vs_service = get_vectorstore_service()
        success = vs_service.delete_vector_store(vector_store_id)
        
        return {
            "status": "success" if success else "failed",
            "vector_store_id": vector_store_id,
        }
        
    except Exception as e:
        print(f"Error deleting vector store {vector_store_id}: {e}")
        raise
