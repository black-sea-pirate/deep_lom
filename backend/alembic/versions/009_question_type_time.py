"""Add time_per_question to question_type_configs

Revision ID: 009_question_type_time
Revises: 008_timer_mode
Create Date: 2026-01-09
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '009_question_type_time'
down_revision = '008_timer_mode'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add time_per_question column to question_type_configs table"""
    op.add_column(
        'question_type_configs',
        sa.Column('time_per_question', sa.Integer(), nullable=False, server_default='60')
    )
    # Remove server default after column is created
    op.alter_column('question_type_configs', 'time_per_question', server_default=None)


def downgrade() -> None:
    """Remove time_per_question column"""
    op.drop_column('question_type_configs', 'time_per_question')
