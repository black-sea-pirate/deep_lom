"""Add num_variants field to projects table

Revision ID: 005_project_num_variants
Revises: 004_test_variants
Create Date: 2025-12-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_project_num_variants'
down_revision = '004_test_variants'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add num_variants to projects table
    # Default 1 for existing projects, can be configured 1-30
    op.add_column(
        'projects',
        sa.Column('num_variants', sa.Integer(), nullable=False, server_default='1')
    )


def downgrade() -> None:
    op.drop_column('projects', 'num_variants')
