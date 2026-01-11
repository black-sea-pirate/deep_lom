"""Add participant_email to tests table

Revision ID: 010_test_participant_email
Revises: 009_question_type_time
Create Date: 2026-01-11

This stores the email address that the teacher knows (participant email),
not the student's primary email. This allows proper display in teacher results.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_test_participant_email'
down_revision = '009_question_type_time'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add participant_email column to tests table
    op.add_column('tests', sa.Column('participant_email', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('tests', 'participant_email')
