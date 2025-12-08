"""Add variant_number to questions and tests

Revision ID: 004_test_variants
Revises: 003_participant_confirmation
Create Date: 2025-12-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_test_variants'
down_revision = '003_participant_confirmation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add variant_number to questions table
    op.add_column(
        'questions',
        sa.Column('variant_number', sa.Integer(), nullable=False, server_default='1')
    )
    
    # Add index for faster variant filtering
    op.create_index(
        'ix_questions_variant_number',
        'questions',
        ['variant_number']
    )
    
    # Add composite index for project + variant queries
    op.create_index(
        'ix_questions_project_variant',
        'questions',
        ['project_id', 'variant_number']
    )
    
    # Add variant_number to tests table
    op.add_column(
        'tests',
        sa.Column('variant_number', sa.Integer(), nullable=False, server_default='1')
    )


def downgrade() -> None:
    op.drop_column('tests', 'variant_number')
    op.drop_index('ix_questions_project_variant', 'questions')
    op.drop_index('ix_questions_variant_number', 'questions')
    op.drop_column('questions', 'variant_number')
    op.drop_column('questions', 'variant_number')
