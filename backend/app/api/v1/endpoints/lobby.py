"""
WebSocket Lobby Endpoints

Real-time WebSocket connections for test lobbies.
Handles teacher and student connections, broadcasts events.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.core.deps import get_db
from app.core.security import verify_token
from app.models.user import User
from app.models.project import Project
from app.services.websocket_manager import get_lobby_manager, LobbyMessage

router = APIRouter()


async def get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """Verify token and get user from database."""
    payload = verify_token(token)
    if not payload:
        return None
    
    result = await db.execute(select(User).where(User.id == payload.sub))
    return result.scalar_one_or_none()


@router.websocket("/ws/lobby/{project_id}/teacher")
async def teacher_lobby_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...),
):
    """
    WebSocket endpoint for teacher to manage lobby.
    
    Query params:
        token: JWT access token
    
    Messages from client:
        - {"action": "start_test"}
        - {"action": "kick_student", "user_id": "..."}
        - {"action": "close_lobby"}
    
    Messages to client:
        - {"type": "lobby_update", "data": {...}}
        - {"type": "student_joined", "data": {...}}
        - {"type": "student_left", "data": {...}}
        - {"type": "student_ready", "data": {...}}
        - {"type": "error", "data": {"message": "..."}}
    """
    # Get database session
    from app.db.session import async_session_maker
    async with async_session_maker() as db:
        # Verify token and get user
        user = await get_user_from_token(token, db)
        if not user or user.role != "teacher":
            await websocket.accept()
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": "Unauthorized"}
            ).to_json())
            await websocket.close()
            return
        
        # Verify project ownership
        result = await db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.teacher_id == user.id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            await websocket.accept()
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": "Project not found"}
            ).to_json())
            await websocket.close()
            return
        
        # Connect to lobby
        manager = get_lobby_manager()
        lobby = await manager.connect_teacher(
            project_id=project_id,
            websocket=websocket,
            user_id=str(user.id),
            max_students=project.max_students or 30,
        )
        
        try:
            while True:
                # Receive messages from teacher
                data = await websocket.receive_text()
                message = json.loads(data)
                action = message.get("action")
                
                if action == "start_test":
                    await manager.start_test(project_id)
                    
                elif action == "kick_student":
                    user_id = message.get("user_id")
                    if user_id:
                        await manager.disconnect_student(project_id, user_id)
                        
                elif action == "close_lobby":
                    await manager.close_lobby(project_id)
                    break
                    
                elif action == "ping":
                    await websocket.send_text(LobbyMessage(
                        type="pong",
                        data={}
                    ).to_json())
                    
        except WebSocketDisconnect:
            # Teacher disconnected - keep lobby open
            pass
        except json.JSONDecodeError:
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": "Invalid message format"}
            ).to_json())
        except Exception as e:
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": str(e)}
            ).to_json())


@router.websocket("/ws/lobby/{project_id}/student")
async def student_lobby_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...),
):
    """
    WebSocket endpoint for student to join lobby.
    
    Query params:
        token: JWT access token
    
    Messages from client:
        - {"action": "ready"}
        - {"action": "not_ready"}
        - {"action": "leave"}
    
    Messages to client:
        - {"type": "lobby_update", "data": {...}}
        - {"type": "test_started", "data": {...}}
        - {"type": "student_joined", "data": {...}}
        - {"type": "student_left", "data": {...}}
        - {"type": "error", "data": {"message": "..."}}
    """
    # Get database session
    from app.db.session import async_session_maker
    async with async_session_maker() as db:
        # Verify token and get user
        user = await get_user_from_token(token, db)
        if not user or user.role != "student":
            await websocket.accept()
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": "Unauthorized"}
            ).to_json())
            await websocket.close()
            return
        
        # Connect to lobby
        manager = get_lobby_manager()
        lobby = await manager.connect_student(
            project_id=project_id,
            websocket=websocket,
            user_id=str(user.id),
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
        )
        
        if not lobby:
            return  # Error already sent in connect_student
        
        try:
            while True:
                # Receive messages from student
                data = await websocket.receive_text()
                message = json.loads(data)
                action = message.get("action")
                
                if action == "ready":
                    await manager.set_student_ready(project_id, str(user.id), True)
                    
                elif action == "not_ready":
                    await manager.set_student_ready(project_id, str(user.id), False)
                    
                elif action == "leave":
                    await manager.disconnect_student(project_id, str(user.id))
                    break
                    
                elif action == "ping":
                    await websocket.send_text(LobbyMessage(
                        type="pong",
                        data={}
                    ).to_json())
                    
        except WebSocketDisconnect:
            await manager.disconnect_student(project_id, str(user.id))
        except json.JSONDecodeError:
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": "Invalid message format"}
            ).to_json())
        except Exception as e:
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": str(e)}
            ).to_json())
