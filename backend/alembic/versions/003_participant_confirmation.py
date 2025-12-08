"""Add confirmation status and student_user_id to participants

Revision ID: 003_participant_confirmation
Revises: 002_openai_vectorstore
Create Date: 2024-12-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_participant_confirmation'
down_revision = '002_openai_vectorstore'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add confirmation_status column with default 'pending'
    op.add_column(
        'participants',
        sa.Column(
            'confirmation_status',
            sa.String(20),
            nullable=False,
            server_default='pending'
        )
    )
    
    # Add student_user_id foreign key column
    op.add_column(
        'participants',
        sa.Column(
            'student_user_id',
            sa.UUID(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        )
    )
    
    # Create index for faster lookups
    op.create_index(
        'ix_participants_confirmation_status',
        'participants',
        ['confirmation_status']
    )
    
    op.create_index(
        'ix_participants_student_user_id',
        'participants',
        ['student_user_id']
    )


def downgrade() -> None:
    op.drop_index('ix_participants_student_user_id', 'participants')
    op.drop_index('ix_participants_confirmation_status', 'participants')
    op.drop_column('participants', 'student_user_id')
    op.drop_column('participants', 'confirmation_status')
