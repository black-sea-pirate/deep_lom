"""Add AI grading details to answers

Revision ID: 007_ai_grading
Revises: 006_test_language
Create Date: 2025-12-08

Adds fields for storing detailed AI grading results:
- ai_grading_details: JSON field with criteria scores and feedback
- graded_by: Who/what graded the answer (ai, manual, system)
- grading_status: Status of grading (pending, completed, failed)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = '007_ai_grading'
down_revision = '006_test_language'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add AI grading fields to answers table
    op.add_column(
        'answers',
        sa.Column(
            'ai_grading_details',
            JSON,
            nullable=True,
            comment='Detailed AI grading results with criteria scores'
        )
    )
    
    op.add_column(
        'answers',
        sa.Column(
            'graded_by',
            sa.String(50),
            nullable=True,
            default='pending',
            comment='Who graded: ai, manual, system, pending_manual_review'
        )
    )
    
    op.add_column(
        'answers',
        sa.Column(
            'grading_status',
            sa.String(20),
            nullable=True,
            default='pending',
            comment='Grading status: pending, in_progress, completed, failed'
        )
    )


def downgrade() -> None:
    op.drop_column('answers', 'grading_status')
    op.drop_column('answers', 'graded_by')
    op.drop_column('answers', 'ai_grading_details')
