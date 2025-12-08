"""
Participant Endpoints

CRUD for participants and groups.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.deps import get_db, get_current_teacher
from app.models.user import User
from app.models.participant import Participant, ParticipantGroup
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantUpdate,
    ParticipantResponse,
    ParticipantListResponse,
    ParticipantGroupCreate,
    ParticipantGroupUpdate,
    ParticipantGroupResponse,
    StudentLookupResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter()


# ============== Student Lookup ==============

@router.get("/lookup", response_model=StudentLookupResponse)
async def lookup_student_by_email(
    email: str = Query(..., description="Email to lookup"),
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Lookup student by email to auto-fill name fields.
    Returns student info if found in users table.
    """
    result = await db.execute(
        select(User).where(
            User.email == email.lower(),
            User.role == "student",
        )
    )
    user = result.scalar_one_or_none()
    
    if user:
        return StudentLookupResponse(
            found=True,
            email=user.email,
            firstName=user.first_name,
            lastName=user.last_name,
            userId=user.id,
        )
    
    return StudentLookupResponse(
        found=False,
        email=email,
        firstName=None,
        lastName=None,
        userId=None,
    )


# ============== Participants ==============

@router.get("", response_model=ParticipantListResponse)
async def get_participants(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    group_id: Optional[UUID] = Query(None, alias="groupId"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all participants for current teacher with pagination.
    """
    query = select(Participant).where(Participant.teacher_id == current_user.id)
    
    # Apply filters
    if group_id:
        query = query.where(Participant.group_id == group_id)
    if search:
        query = query.where(
            (Participant.email.ilike(f"%{search}%")) |
            (Participant.first_name.ilike(f"%{search}%")) |
            (Participant.last_name.ilike(f"%{search}%"))
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.order_by(Participant.last_name, Participant.first_name)
    query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    participants = result.scalars().all()
    
    return ParticipantListResponse(
        items=[
            ParticipantResponse(
                id=p.id,
                email=p.email,
                firstName=p.first_name,
                lastName=p.last_name,
                type=p.participant_type,
                groupId=p.group_id,
                confirmationStatus=p.confirmation_status,
                studentUserId=p.student_user_id,
                createdAt=p.created_at,
            )
            for p in participants
        ],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.post("", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
async def create_participant(
    participant_data: ParticipantCreate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new participant.
    If auto_fill is True, will lookup student info from database.
    """
    # Check if email already exists for this teacher
    existing = await db.execute(
        select(Participant).where(
            Participant.teacher_id == current_user.id,
            Participant.email == participant_data.email.lower(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant with this email already exists",
        )
    
    first_name = participant_data.first_name
    last_name = participant_data.last_name
    student_user_id = None
    
    # Auto-fill from database if requested
    if participant_data.auto_fill:
        user_result = await db.execute(
            select(User).where(
                User.email == participant_data.email.lower(),
                User.role == "student",
            )
        )
        student_user = user_result.scalar_one_or_none()
        
        if student_user:
            first_name = student_user.first_name
            last_name = student_user.last_name
            student_user_id = student_user.id
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student with this email not found in database",
            )
    else:
        # Try to find student user anyway (for linking)
        user_result = await db.execute(
            select(User).where(
                User.email == participant_data.email.lower(),
                User.role == "student",
            )
        )
        student_user = user_result.scalar_one_or_none()
        if student_user:
            student_user_id = student_user.id
    
    participant = Participant(
        teacher_id=current_user.id,
        student_user_id=student_user_id,
        email=participant_data.email.lower(),
        first_name=first_name,
        last_name=last_name,
        participant_type=participant_data.participant_type,
        group_id=participant_data.group_id,
        confirmation_status="pending",
    )
    
    db.add(participant)
    await db.commit()
    await db.refresh(participant)
    
    return ParticipantResponse(
        id=participant.id,
        email=participant.email,
        firstName=participant.first_name,
        lastName=participant.last_name,
        type=participant.participant_type,
        groupId=participant.group_id,
        confirmationStatus=participant.confirmation_status,
        studentUserId=participant.student_user_id,
        createdAt=participant.created_at,
    )


@router.put("/{participant_id}", response_model=ParticipantResponse)
async def update_participant(
    participant_id: UUID,
    participant_data: ParticipantUpdate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Update participant by ID.
    """
    query = select(Participant).where(
        Participant.id == participant_id,
        Participant.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )
    
    if participant_data.email is not None:
        participant.email = participant_data.email
    if participant_data.first_name is not None:
        participant.first_name = participant_data.first_name
    if participant_data.last_name is not None:
        participant.last_name = participant_data.last_name
    if participant_data.group_id is not None:
        participant.group_id = participant_data.group_id
    
    await db.commit()
    await db.refresh(participant)
    
    return ParticipantResponse(
        id=participant.id,
        email=participant.email,
        firstName=participant.first_name,
        lastName=participant.last_name,
        type=participant.participant_type,
        groupId=participant.group_id,
        confirmationStatus=participant.confirmation_status,
        studentUserId=participant.student_user_id,
        createdAt=participant.created_at,
    )


@router.delete("/{participant_id}", response_model=MessageResponse)
async def delete_participant(
    participant_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete participant by ID.
    """
    query = select(Participant).where(
        Participant.id == participant_id,
        Participant.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )
    
    await db.delete(participant)
    await db.commit()
    
    return MessageResponse(message="Participant deleted successfully")


# ============== Groups ==============

@router.get("/groups", response_model=list[ParticipantGroupResponse])
async def get_groups(
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all groups for current teacher.
    """
    query = select(ParticipantGroup).where(ParticipantGroup.teacher_id == current_user.id)
    query = query.order_by(ParticipantGroup.name)
    
    result = await db.execute(query)
    groups = result.scalars().all()
    
    response = []
    for group in groups:
        # Count members
        count_query = select(func.count()).where(Participant.group_id == group.id)
        count_result = await db.execute(count_query)
        members_count = count_result.scalar() or 0
        
        response.append(
            ParticipantGroupResponse(
                id=group.id,
                teacherId=group.teacher_id,
                name=group.name,
                description=group.description,
                membersCount=members_count,
                createdAt=group.created_at,
            )
        )
    
    return response


@router.post("/groups", response_model=ParticipantGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: ParticipantGroupCreate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new group.
    """
    group = ParticipantGroup(
        teacher_id=current_user.id,
        name=group_data.name,
        description=group_data.description,
    )
    
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return ParticipantGroupResponse(
        id=group.id,
        teacherId=group.teacher_id,
        name=group.name,
        description=group.description,
        membersCount=0,
        createdAt=group.created_at,
    )


@router.put("/groups/{group_id}", response_model=ParticipantGroupResponse)
async def update_group(
    group_id: UUID,
    group_data: ParticipantGroupUpdate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Update group by ID.
    """
    query = select(ParticipantGroup).where(
        ParticipantGroup.id == group_id,
        ParticipantGroup.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    if group_data.name is not None:
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description
    
    await db.commit()
    await db.refresh(group)
    
    # Count members
    count_query = select(func.count()).where(Participant.group_id == group.id)
    count_result = await db.execute(count_query)
    members_count = count_result.scalar() or 0
    
    return ParticipantGroupResponse(
        id=group.id,
        teacherId=group.teacher_id,
        name=group.name,
        description=group.description,
        membersCount=members_count,
        createdAt=group.created_at,
    )


@router.delete("/groups/{group_id}", response_model=MessageResponse)
async def delete_group(
    group_id: UUID,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete group by ID.
    Members are not deleted, just unlinked from the group.
    """
    query = select(ParticipantGroup).where(
        ParticipantGroup.id == group_id,
        ParticipantGroup.teacher_id == current_user.id,
    )
    
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    # Unlink participants from group
    participants_query = select(Participant).where(Participant.group_id == group_id)
    participants_result = await db.execute(participants_query)
    for participant in participants_result.scalars():
        participant.group_id = None
        participant.participant_type = "individual"
    
    await db.delete(group)
    await db.commit()
    
    return MessageResponse(message="Group deleted successfully")
