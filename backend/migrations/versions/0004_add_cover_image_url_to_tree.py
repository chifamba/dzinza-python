"""add_cover_image_url_to_tree

Revision ID: 0004
Revises: 0003
Create Date: 2024-04-08 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('trees', sa.Column('cover_image_url', sa.String(length=512), nullable=True))


def downgrade():
    op.drop_column('trees', 'cover_image_url')
