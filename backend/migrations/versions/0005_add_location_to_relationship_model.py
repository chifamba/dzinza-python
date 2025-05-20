"""add_location_to_relationship_model

Revision ID: 0005
Revises: 0004
Create Date: 2024-04-08 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004' # Points to the migration for adding cover_image_url to trees
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('relationships', sa.Column('location', sa.String(length=255), nullable=True))
    # The 'notes' field (Text) should already exist in the Relationship model as per Task 1.6.
    # If it didn't, it would be added here as well.
    # op.add_column('relationships', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('relationships', 'location')
    # If 'notes' were added in this migration's upgrade:
    # op.drop_column('relationships', 'notes')
