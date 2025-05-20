"""add_custom_fields_to_person

Revision ID: 0002
Revises: 0001
Create Date: 2024-04-08 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('people', sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")))


def downgrade():
    op.drop_column('people', 'custom_fields')
