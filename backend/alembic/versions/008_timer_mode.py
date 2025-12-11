"""Add timer_mode field to projects

Revision ID: 008_timer_mode
Revises: 007_ai_grading
Create Date: 2025-12-11

Timer mode allows choosing between:
- 'total': Use total_time (minutes) for entire test
- 'per_question': Use time_per_question (seconds) per each question
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_timer_mode'
down_revision = '007_ai_grading'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add timer_mode column with default 'total'
    op.add_column(
        'projects',
        sa.Column('timer_mode', sa.String(20), nullable=False, server_default='total')
    )


def downgrade() -> None:
    op.drop_column('projects', 'timer_mode')
