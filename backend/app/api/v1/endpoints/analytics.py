"""
Analytics Endpoints

Teacher analytics and reporting.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.core.deps import get_db, get_current_teacher
from app.models.user import User
from app.models.project import Project
from app.models.test import Test
from app.models.participant import Participant

router = APIRouter()


def get_period_start(period: str) -> datetime:
    """Calculate start date based on period."""
    now = datetime.utcnow()
    if period == "week":
        return now - timedelta(days=7)
    elif period == "month":
        return now - timedelta(days=30)
    elif period == "quarter":
        return now - timedelta(days=90)
    elif period == "year":
        return now - timedelta(days=365)
    else:  # all
        return datetime(2000, 1, 1)


@router.get("")
async def get_analytics(
    period: str = Query("month", description="Time period: week, month, quarter, year, all"),
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive analytics for teacher.
    """
    period_start = get_period_start(period)
    prev_period_start = get_period_start(period) - (datetime.utcnow() - get_period_start(period))
    
    # Get teacher's projects
    projects_query = select(Project.id).where(Project.teacher_id == current_user.id)
    projects_result = await db.execute(projects_query)
    project_ids = [p[0] for p in projects_result.all()]
    
    if not project_ids:
        return {
            "overview": {
                "totalTests": 0,
                "totalStudents": 0,
                "avgScore": 0,
                "completionRate": 0,
                "avgTimeMinutes": 0,
                "testsThisMonth": 0,
                "scoreChange": 0,
                "studentsChange": 0,
            },
            "scoreDistribution": [],
            "recentTests": [],
            "topStudents": [],
            "projectPerformance": [],
        }
    
    # Total tests count
    total_tests_query = select(func.count()).where(
        Test.project_id.in_(project_ids),
        Test.status == "completed",
    )
    total_result = await db.execute(total_tests_query)
    total_tests = total_result.scalar() or 0
    
    # Tests this period
    period_tests_query = select(func.count()).where(
        Test.project_id.in_(project_ids),
        Test.status == "completed",
        Test.completed_at >= period_start,
    )
    period_result = await db.execute(period_tests_query)
    tests_this_period = period_result.scalar() or 0
    
    # Total unique students
    students_query = select(func.count(func.distinct(Test.student_id))).where(
        Test.project_id.in_(project_ids),
        Test.student_id.isnot(None),
    )
    students_result = await db.execute(students_query)
    total_students = students_result.scalar() or 0
    
    # New students this period
    new_students_query = select(func.count(func.distinct(Test.student_id))).where(
        Test.project_id.in_(project_ids),
        Test.student_id.isnot(None),
        Test.created_at >= period_start,
    )
    new_students_result = await db.execute(new_students_query)
    new_students = new_students_result.scalar() or 0
    
    # Average score
    avg_score_query = select(
        func.avg(Test.score * 100.0 / Test.max_score)
    ).where(
        Test.project_id.in_(project_ids),
        Test.status == "completed",
        Test.max_score > 0,
    )
    avg_result = await db.execute(avg_score_query)
    avg_score = avg_result.scalar() or 0
    
    # Previous period avg score for comparison
    prev_avg_query = select(
        func.avg(Test.score * 100.0 / Test.max_score)
    ).where(
        Test.project_id.in_(project_ids),
        Test.status == "completed",
        Test.max_score > 0,
        Test.completed_at >= prev_period_start,
        Test.completed_at < period_start,
    )
    prev_avg_result = await db.execute(prev_avg_query)
    prev_avg_score = prev_avg_result.scalar() or avg_score
    score_change = round(avg_score - prev_avg_score, 1) if prev_avg_score else 0
    
    # Completion rate (completed / total started)
    started_query = select(func.count()).where(
        Test.project_id.in_(project_ids),
        Test.status.in_(["in-progress", "completed"]),
    )
    started_result = await db.execute(started_query)
    started_count = started_result.scalar() or 1
    completion_rate = round((total_tests / started_count) * 100, 1) if started_count > 0 else 0
    
    # Score distribution
    score_dist = []
    ranges = [(0, 20), (21, 40), (41, 60), (61, 80), (81, 100)]
    for min_score, max_score in ranges:
        count_query = select(func.count()).where(
            Test.project_id.in_(project_ids),
            Test.status == "completed",
            Test.max_score > 0,
            (Test.score * 100.0 / Test.max_score) >= min_score,
            (Test.score * 100.0 / Test.max_score) <= max_score,
        )
        count_result = await db.execute(count_query)
        count = count_result.scalar() or 0
        percentage = round((count / total_tests) * 100, 1) if total_tests > 0 else 0
        score_dist.append({
            "range": f"{min_score}-{max_score}",
            "count": count,
            "percentage": percentage,
        })
    
    # Recent tests
    recent_tests_query = select(
        Test.project_id,
        Project.title,
        func.max(Test.completed_at).label("date"),
        func.count(Test.id).label("participants"),
        func.avg(Test.score * 100.0 / Test.max_score).label("avgScore"),
    ).join(Project, Test.project_id == Project.id).where(
        Test.project_id.in_(project_ids),
        Test.status == "completed",
    ).group_by(Test.project_id, Project.title).order_by(
        func.max(Test.completed_at).desc()
    ).limit(5)
    
    recent_result = await db.execute(recent_tests_query)
    recent_tests = []
    for row in recent_result.all():
        # Calculate pass rate
        pass_query = select(func.count()).where(
            Test.project_id == row.project_id,
            Test.status == "completed",
            Test.max_score > 0,
            (Test.score * 100.0 / Test.max_score) >= 60,
        )
        pass_result = await db.execute(pass_query)
        passed = pass_result.scalar() or 0
        pass_rate = round((passed / row.participants) * 100, 1) if row.participants > 0 else 0
        
        recent_tests.append({
            "id": str(row.project_id),
            "projectName": row.title,
            "date": row.date.isoformat() if row.date else None,
            "participants": row.participants,
            "avgScore": round(row.avgScore or 0, 1),
            "passRate": pass_rate,
        })
    
    # Top students
    top_students_query = select(
        Test.student_id,
        User.first_name,
        User.last_name,
        func.avg(Test.score * 100.0 / Test.max_score).label("avgScore"),
        func.count(Test.id).label("testsCompleted"),
    ).join(User, Test.student_id == User.id).where(
        Test.project_id.in_(project_ids),
        Test.status == "completed",
        Test.student_id.isnot(None),
        Test.max_score > 0,
    ).group_by(Test.student_id, User.first_name, User.last_name).order_by(
        func.avg(Test.score * 100.0 / Test.max_score).desc()
    ).limit(5)
    
    top_result = await db.execute(top_students_query)
    top_students = [
        {
            "id": str(row.student_id),
            "name": f"{row.first_name} {row.last_name}",
            "avgScore": round(row.avgScore or 0, 1),
            "testsCompleted": row.testsCompleted,
        }
        for row in top_result.all()
    ]
    
    # Project performance
    proj_perf_query = select(
        Project.id,
        Project.title,
        func.avg(Test.score * 100.0 / Test.max_score).label("avgScore"),
        func.count(Test.id).label("tests"),
        func.count(func.distinct(Test.student_id)).label("students"),
    ).join(Test, Project.id == Test.project_id).where(
        Project.teacher_id == current_user.id,
        Test.status == "completed",
        Test.max_score > 0,
    ).group_by(Project.id, Project.title)
    
    proj_result = await db.execute(proj_perf_query)
    project_performance = [
        {
            "name": row.title,
            "avgScore": round(row.avgScore or 0, 1),
            "tests": row.tests,
            "students": row.students,
            "trend": "stable",  # Could be calculated from historical data
        }
        for row in proj_result.all()
    ]
    
    return {
        "overview": {
            "totalTests": total_tests,
            "totalStudents": total_students,
            "avgScore": round(avg_score, 1),
            "completionRate": completion_rate,
            "avgTimeMinutes": 45,  # Would need to track this
            "testsThisMonth": tests_this_period,
            "scoreChange": score_change,
            "studentsChange": new_students,
        },
        "scoreDistribution": score_dist,
        "recentTests": recent_tests,
        "topStudents": top_students,
        "projectPerformance": project_performance,
    }
