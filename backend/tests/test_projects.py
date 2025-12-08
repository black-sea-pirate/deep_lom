"""
Projects API Tests

Tests for project CRUD operations and test generation.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.user import User


class TestProjectCreate:
    """Tests for project creation endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_project_success(
        self, client: AsyncClient, teacher_headers, test_teacher
    ):
        """Test successful project creation."""
        response = await client.post(
            "/api/v1/projects",
            headers=teacher_headers,
            json={
                "title": "Test Project",
                "description": "A test project for unit tests",
                "group_name": "TEST-101",
                "total_time": 60,
                "time_per_question": 120,
                "max_students": 30,
                "question_types": [
                    {"type": "single-choice", "count": 5},
                    {"type": "multiple-choice", "count": 3},
                ],
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Project"
        assert data["status"] == "draft"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_project_student_forbidden(
        self, client: AsyncClient, student_headers
    ):
        """Test that students cannot create projects."""
        response = await client.post(
            "/api/v1/projects",
            headers=student_headers,
            json={
                "title": "Student Project",
                "description": "Should fail",
                "group_name": "FAIL-101",
            },
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_create_project_no_auth(self, client: AsyncClient):
        """Test project creation without authentication."""
        response = await client.post(
            "/api/v1/projects",
            json={
                "title": "No Auth Project",
                "description": "Should fail",
                "group_name": "FAIL-101",
            },
        )
        
        assert response.status_code == 401


class TestProjectList:
    """Tests for project listing endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_projects_empty(
        self, client: AsyncClient, teacher_headers
    ):
        """Test listing projects when none exist."""
        response = await client.get(
            "/api/v1/projects",
            headers=teacher_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_projects_with_data(
        self, client: AsyncClient, teacher_headers, async_session, test_teacher
    ):
        """Test listing projects with existing data."""
        # Create test projects
        for i in range(3):
            project = Project(
                title=f"Project {i}",
                description=f"Description {i}",
                group_name=f"GROUP-{i}",
                teacher_id=test_teacher.id,
            )
            async_session.add(project)
        await async_session.commit()
        
        response = await client.get(
            "/api/v1/projects",
            headers=teacher_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
    
    @pytest.mark.asyncio
    async def test_list_projects_pagination(
        self, client: AsyncClient, teacher_headers, async_session, test_teacher
    ):
        """Test project listing with pagination."""
        # Create 15 projects
        for i in range(15):
            project = Project(
                title=f"Project {i}",
                teacher_id=test_teacher.id,
            )
            async_session.add(project)
        await async_session.commit()
        
        # Get first page
        response = await client.get(
            "/api/v1/projects?page=1&size=10",
            headers=teacher_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["items"]) == 10
        assert data["page"] == 1
        
        # Get second page
        response = await client.get(
            "/api/v1/projects?page=2&size=10",
            headers=teacher_headers,
        )
        
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2


class TestProjectGet:
    """Tests for getting single project."""
    
    @pytest.mark.asyncio
    async def test_get_project_success(
        self, client: AsyncClient, teacher_headers, async_session, test_teacher
    ):
        """Test getting a project by ID."""
        project = Project(
            title="Get Test Project",
            description="Test description",
            teacher_id=test_teacher.id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)
        
        response = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=teacher_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Get Test Project"
    
    @pytest.mark.asyncio
    async def test_get_project_not_found(
        self, client: AsyncClient, teacher_headers
    ):
        """Test getting non-existent project."""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = await client.get(
            f"/api/v1/projects/{fake_id}",
            headers=teacher_headers,
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_project_other_teacher(
        self, client: AsyncClient, teacher_headers, async_session
    ):
        """Test getting project belonging to another teacher."""
        from app.core.security import get_password_hash
        
        # Create another teacher
        other_teacher = User(
            email="other@test.com",
            hashed_password=get_password_hash("password"),
            first_name="Other",
            last_name="Teacher",
            role="teacher",
        )
        async_session.add(other_teacher)
        await async_session.commit()
        
        # Create project for other teacher
        project = Project(
            title="Other's Project",
            teacher_id=other_teacher.id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)
        
        response = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=teacher_headers,
        )
        
        assert response.status_code == 404


class TestProjectUpdate:
    """Tests for project update endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_project_success(
        self, client: AsyncClient, teacher_headers, async_session, test_teacher
    ):
        """Test successful project update."""
        project = Project(
            title="Original Title",
            description="Original description",
            teacher_id=test_teacher.id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)
        
        response = await client.patch(
            f"/api/v1/projects/{project.id}",
            headers=teacher_headers,
            json={
                "title": "Updated Title",
                "description": "Updated description",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_update_project_status(
        self, client: AsyncClient, teacher_headers, async_session, test_teacher
    ):
        """Test updating project status."""
        project = Project(
            title="Status Test",
            teacher_id=test_teacher.id,
            status="draft",
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)
        
        response = await client.patch(
            f"/api/v1/projects/{project.id}",
            headers=teacher_headers,
            json={"status": "ready"},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


class TestProjectDelete:
    """Tests for project deletion endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_project_success(
        self, client: AsyncClient, teacher_headers, async_session, test_teacher
    ):
        """Test successful project deletion."""
        project = Project(
            title="To Delete",
            teacher_id=test_teacher.id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)
        
        response = await client.delete(
            f"/api/v1/projects/{project.id}",
            headers=teacher_headers,
        )
        
        assert response.status_code == 200
        
        # Verify deletion
        response = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=teacher_headers,
        )
        assert response.status_code == 404
