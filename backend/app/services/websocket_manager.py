"""
WebSocket Lobby Manager

Manages real-time connections for test lobbies.
Handles student join/leave events and test start broadcasts.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID
from dataclasses import dataclass, asdict
from fastapi import WebSocket, WebSocketDisconnect
import asyncio


@dataclass
class LobbyStudent:
    """Student connected to a lobby."""
    user_id: str
    first_name: str
    last_name: str
    email: str
    status: str = "waiting"  # waiting, ready
    joined_at: str = ""
    
    def __post_init__(self):
        if not self.joined_at:
            self.joined_at = datetime.utcnow().isoformat()
    
    def to_dict(self):
        return asdict(self)


@dataclass
class LobbyMessage:
    """WebSocket message structure."""
    type: str  # student_joined, student_left, student_ready, test_started, lobby_update, error
    data: dict
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))


class LobbyConnection:
    """Single WebSocket connection with metadata."""
    
    def __init__(self, websocket: WebSocket, user_id: str, user_role: str):
        self.websocket = websocket
        self.user_id = user_id
        self.user_role = user_role
        self.connected_at = datetime.utcnow()
    
    async def send(self, message: LobbyMessage):
        """Send message to this connection."""
        try:
            await self.websocket.send_text(message.to_json())
        except Exception:
            pass  # Connection might be closed


class Lobby:
    """Single project lobby with connected users."""
    
    def __init__(self, project_id: str, max_students: int = 30):
        self.project_id = project_id
        self.max_students = max_students
        self.status = "waiting"  # waiting, active, completed
        self.created_at = datetime.utcnow()
        
        # Connected clients
        self.teacher_connection: Optional[LobbyConnection] = None
        self.student_connections: Dict[str, LobbyConnection] = {}
        self.students: Dict[str, LobbyStudent] = {}
    
    @property
    def student_count(self) -> int:
        return len(self.students)
    
    @property
    def is_full(self) -> bool:
        return self.student_count >= self.max_students
    
    def get_students_list(self) -> List[dict]:
        """Get list of all students in lobby."""
        return [s.to_dict() for s in self.students.values()]
    
    async def broadcast(self, message: LobbyMessage, exclude_user: Optional[str] = None):
        """Broadcast message to all connected users."""
        tasks = []
        
        # Send to teacher
        if self.teacher_connection and self.teacher_connection.user_id != exclude_user:
            tasks.append(self.teacher_connection.send(message))
        
        # Send to all students
        for user_id, conn in self.student_connections.items():
            if user_id != exclude_user:
                tasks.append(conn.send(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_lobby_update(self):
        """Send current lobby state to all connected users."""
        message = LobbyMessage(
            type="lobby_update",
            data={
                "project_id": self.project_id,
                "status": self.status,
                "students": self.get_students_list(),
                "student_count": self.student_count,
                "max_students": self.max_students,
            }
        )
        await self.broadcast(message)


class LobbyManager:
    """
    Manages all active lobbies.
    
    Provides methods for:
    - Creating/closing lobbies
    - Handling student join/leave
    - Broadcasting lobby events
    - Starting tests
    """
    
    def __init__(self):
        self.lobbies: Dict[str, Lobby] = {}
        self._lock = asyncio.Lock()
    
    def get_or_create_lobby(self, project_id: str, max_students: int = 30) -> Lobby:
        """Get existing lobby or create new one."""
        if project_id not in self.lobbies:
            self.lobbies[project_id] = Lobby(project_id, max_students)
        return self.lobbies[project_id]
    
    def get_lobby(self, project_id: str) -> Optional[Lobby]:
        """Get existing lobby if it exists."""
        return self.lobbies.get(project_id)
    
    async def close_lobby(self, project_id: str):
        """Close lobby and disconnect all users."""
        async with self._lock:
            lobby = self.lobbies.pop(project_id, None)
            if lobby:
                # Notify all users
                message = LobbyMessage(
                    type="lobby_closed",
                    data={"project_id": project_id, "reason": "Lobby closed by teacher"}
                )
                await lobby.broadcast(message)
                
                # Close all connections
                if lobby.teacher_connection:
                    try:
                        await lobby.teacher_connection.websocket.close()
                    except Exception:
                        pass
                
                for conn in lobby.student_connections.values():
                    try:
                        await conn.websocket.close()
                    except Exception:
                        pass
    
    async def connect_teacher(
        self,
        project_id: str,
        websocket: WebSocket,
        user_id: str,
        max_students: int = 30,
    ):
        """Connect teacher to lobby."""
        await websocket.accept()
        
        async with self._lock:
            lobby = self.get_or_create_lobby(project_id, max_students)
            lobby.teacher_connection = LobbyConnection(websocket, user_id, "teacher")
        
        # Send current lobby state
        await lobby.broadcast_lobby_update()
        
        return lobby
    
    async def connect_student(
        self,
        project_id: str,
        websocket: WebSocket,
        user_id: str,
        first_name: str,
        last_name: str,
        email: str,
    ) -> Optional[Lobby]:
        """Connect student to lobby."""
        lobby = self.get_lobby(project_id)
        
        if not lobby:
            await websocket.accept()
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": "Lobby not found"}
            ).to_json())
            await websocket.close()
            return None
        
        if lobby.is_full:
            await websocket.accept()
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": "Lobby is full"}
            ).to_json())
            await websocket.close()
            return None
        
        if lobby.status != "waiting":
            await websocket.accept()
            await websocket.send_text(LobbyMessage(
                type="error",
                data={"message": "Test already started"}
            ).to_json())
            await websocket.close()
            return None
        
        await websocket.accept()
        
        async with self._lock:
            # Add student to lobby
            student = LobbyStudent(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )
            lobby.students[user_id] = student
            lobby.student_connections[user_id] = LobbyConnection(websocket, user_id, "student")
        
        # Broadcast student joined
        message = LobbyMessage(
            type="student_joined",
            data=student.to_dict()
        )
        await lobby.broadcast(message, exclude_user=user_id)
        
        # Send lobby state to new student
        await lobby.broadcast_lobby_update()
        
        return lobby
    
    async def disconnect_student(self, project_id: str, user_id: str):
        """Disconnect student from lobby."""
        lobby = self.get_lobby(project_id)
        if not lobby:
            return
        
        async with self._lock:
            student = lobby.students.pop(user_id, None)
            lobby.student_connections.pop(user_id, None)
        
        if student:
            # Broadcast student left
            message = LobbyMessage(
                type="student_left",
                data={"user_id": user_id, "name": f"{student.first_name} {student.last_name}"}
            )
            await lobby.broadcast(message)
            await lobby.broadcast_lobby_update()
    
    async def set_student_ready(self, project_id: str, user_id: str, is_ready: bool = True):
        """Set student ready status."""
        lobby = self.get_lobby(project_id)
        if not lobby or user_id not in lobby.students:
            return
        
        lobby.students[user_id].status = "ready" if is_ready else "waiting"
        
        # Broadcast status change
        message = LobbyMessage(
            type="student_ready",
            data={
                "user_id": user_id,
                "status": lobby.students[user_id].status,
            }
        )
        await lobby.broadcast(message)
        await lobby.broadcast_lobby_update()
    
    async def start_test(self, project_id: str):
        """Start test for all students in lobby."""
        lobby = self.get_lobby(project_id)
        if not lobby:
            return False
        
        async with self._lock:
            lobby.status = "active"
        
        # Broadcast test started
        message = LobbyMessage(
            type="test_started",
            data={
                "project_id": project_id,
                "started_at": datetime.utcnow().isoformat(),
            }
        )
        await lobby.broadcast(message)
        
        return True
    
    async def complete_test(self, project_id: str):
        """Mark test as completed."""
        lobby = self.get_lobby(project_id)
        if not lobby:
            return
        
        async with self._lock:
            lobby.status = "completed"
        
        # Broadcast test completed
        message = LobbyMessage(
            type="test_completed",
            data={"project_id": project_id}
        )
        await lobby.broadcast(message)
        
        # Close lobby after delay
        await asyncio.sleep(5)
        await self.close_lobby(project_id)


# Global lobby manager instance
lobby_manager = LobbyManager()


def get_lobby_manager() -> LobbyManager:
    """Get the global lobby manager instance."""
    return lobby_manager
