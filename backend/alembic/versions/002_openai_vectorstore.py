"""Add OpenAI Vector Store fields

Revision ID: 002_openai_vectorstore
Revises: 001_initial
Create Date: 2025-01-20

This migration:
1. Removes chroma_collection_id from projects table
2. Adds openai_vector_store_id and openai_assistant_id to projects
3. Adds openai_file_id to materials
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_openai_vectorstore'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove old ChromaDB column
    op.drop_column('projects', 'chroma_collection_id')
    
    # Add OpenAI Vector Store columns to projects
    op.add_column('projects', sa.Column('openai_vector_store_id', sa.String(255), nullable=True))
    op.add_column('projects', sa.Column('openai_assistant_id', sa.String(255), nullable=True))
    
    # Add OpenAI file ID to materials
    op.add_column('materials', sa.Column('openai_file_id', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove OpenAI columns
    op.drop_column('materials', 'openai_file_id')
    op.drop_column('projects', 'openai_assistant_id')
    op.drop_column('projects', 'openai_vector_store_id')
    
    # Restore ChromaDB column
    op.add_column('projects', sa.Column('chroma_collection_id', sa.String(255), nullable=True))
