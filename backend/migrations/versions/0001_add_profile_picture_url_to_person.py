"""add_profile_picture_url_to_person

Revision ID: 0001
Revises: 
Create Date: 2024-04-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None  # Assuming this is the first migration
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('people', sa.Column('profile_picture_url', sa.String(length=512), nullable=True))


def downgrade():
    op.drop_column('people', 'profile_picture_url')
