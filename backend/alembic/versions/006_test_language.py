"""Add test_language column to projects

Revision ID: 006_test_language
Revises: 005_project_num_variants
Create Date: 2025-12-06

Adds test_language column to store the language for generated test questions.
This allows teachers to generate questions in any language regardless of 
the source material language.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '006_test_language'
down_revision = '005_project_num_variants'
branch_labels = None
depends_on = None


def upgrade():
    """Add test_language column to projects table"""
    op.add_column(
        'projects',
        sa.Column(
            'test_language',
            sa.String(10),
            nullable=False,
            server_default='en'  # Default to English
        )
    )


def downgrade():
    """Remove test_language column from projects table"""
    op.drop_column('projects', 'test_language')
