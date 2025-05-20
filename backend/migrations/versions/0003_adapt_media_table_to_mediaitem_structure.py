"""adapt_media_table_to_mediaitem_structure

Revision ID: 0003
Revises: 0002
Create Date: 2024-04-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# It's generally better if MediaTypeEnum can be imported,
# but for simplicity in migrations if it's complex or causes issues,
# defining it here or using sa.Enum directly is an alternative.
# For this case, we'll assume direct sa.Enum usage for file_type is fine
# if models.MediaTypeEnum is not easily accessible in migration context.
# However, the model already defines `media_type` with SQLAlchemyEnum, so altering should be fine.

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # Rename columns
    op.alter_column('media', 'created_by', new_column_name='uploader_user_id', existing_type=postgresql.UUID(as_uuid=True), existing_nullable=False, existing_server_default=None)
    op.alter_column('media', 'original_filename', new_column_name='file_name', existing_type=sa.String(length=255), nullable=False) # Make non-nullable
    op.alter_column('media', 'file_path', new_column_name='storage_path', existing_type=sa.String(length=512), existing_nullable=False)
    op.alter_column('media', 'description', new_column_name='caption', existing_type=sa.Text(), nullable=True) # Keep nullable if it was
    op.alter_column('media', 'uploaded_at', new_column_name='created_at', existing_type=sa.DateTime(), existing_nullable=True, existing_server_default=sa.text('now()'))
    
    # Add new columns
    op.add_column('media', sa.Column('linked_entity_type', sa.String(length=50), nullable=False, index=True))
    op.add_column('media', sa.Column('linked_entity_id', postgresql.UUID(as_uuid=True), nullable=False, index=True))
    op.add_column('media', sa.Column('thumbnail_url', sa.String(length=512), nullable=True))

    # Ensure media_type (now file_type in model) is non-nullable if it wasn't explicitly
    # The model already has `nullable=False` for `file_type` (previously `media_type`)
    # So, if the column was already non-nullable, this is fine. If it could be nullable, we might need:
    # op.alter_column('media', 'media_type', nullable=False) 
    # (Note: model renames media_type to file_type, but DB column name is media_type unless changed by prior migration)
    # The model uses `file_type = Column(SQLAlchemyEnum(MediaTypeEnum...` so the column name is `file_type` if created by SQLAlchemy from scratch
    # or `media_type` if that was the original name. The model change was `file_type = Column(SQLAlchemyEnum(MediaTypeEnum...`.
    # The table `media` had `media_type`. So we ensure `media_type` is non-nullable.
    op.alter_column('media', 'media_type', nullable=False)


    # Drop old columns
    op.drop_column('media', 'storage_bucket')
    op.drop_column('media', 'title')
    op.drop_column('media', 'date_taken')
    op.drop_column('media', 'location')
    op.drop_column('media', 'media_metadata')
    op.drop_column('media', 'privacy_level')

    # Create indexes for new columns if not already created by nullable=False, index=True in add_column
    # op.create_index(op.f('ix_media_linked_entity_type'), 'media', ['linked_entity_type'], unique=False) # Already created by index=True
    # op.create_index(op.f('ix_media_linked_entity_id'), 'media', ['linked_entity_id'], unique=False) # Already created by index=True


def downgrade():
    # Revert dropped columns (add them back as they were)
    # Note: Data is lost. For EncryptedString, use sa.Text or sa.String appropriately.
    op.add_column('media', sa.Column('privacy_level', sa.String(length=50), nullable=True)) # Assuming it was a string based enum
    op.add_column('media', sa.Column('media_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=True))
    op.add_column('media', sa.Column('location', sa.Text(), nullable=True)) # Assuming EncryptedString was Text
    op.add_column('media', sa.Column('date_taken', sa.Date(), nullable=True))
    op.add_column('media', sa.Column('title', sa.String(length=255), nullable=True, index=True))
    op.add_column('media', sa.Column('storage_bucket', sa.String(length=255), nullable=False, server_default="default_bucket")) # Made up server_default

    # Revert added columns
    op.drop_column('media', 'thumbnail_url')
    # op.drop_index(op.f('ix_media_linked_entity_id'), table_name='media') # if index was explicitly created
    op.drop_column('media', 'linked_entity_id')
    # op.drop_index(op.f('ix_media_linked_entity_type'), table_name='media') # if index was explicitly created
    op.drop_column('media', 'linked_entity_type')

    # Revert renamed columns
    op.alter_column('media', 'created_at', new_column_name='uploaded_at', existing_type=sa.DateTime(), existing_nullable=True, existing_server_default=sa.text('now()'))
    op.alter_column('media', 'caption', new_column_name='description', existing_type=sa.Text(), nullable=True)
    op.alter_column('media', 'storage_path', new_column_name='file_path', existing_type=sa.String(length=512), existing_nullable=False)
    op.alter_column('media', 'file_name', new_column_name='original_filename', existing_type=sa.String(length=255), nullable=True) # Revert nullable
    op.alter_column('media', 'uploader_user_id', new_column_name='created_by', existing_type=postgresql.UUID(as_uuid=True), existing_nullable=False)
    
    # Revert nullable change for media_type (now file_type in model) if it was changed
    # op.alter_column('media', 'media_type', nullable=True) # If it was made non-nullable in upgrade
    # This depends on original schema. Assuming it was already nullable=False from model def.
    # The model had nullable=False for media_type, so this line is not strictly needed unless we changed it to True before.
    # If the original was nullable=True, and upgrade made it False, then this should be nullable=True.
    # Based on the model, it was nullable=False.
    pass # No change needed for media_type nullability if it was always False.
