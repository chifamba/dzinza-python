"""implement_tree_privacy_settings

Revision ID: 0006
Revises: 0005
Create Date: 2024-04-08 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Define the enum directly in the migration for data migration steps
# This ensures the migration is self-contained regarding this enum's values.
tree_privacy_setting_enum = sa.Enum('PUBLIC', 'PRIVATE', name='treeprivacysettingenum')

# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add the new privacy_setting column, initially nullable for data migration
    op.add_column('trees', sa.Column('privacy_setting', tree_privacy_setting_enum, nullable=True))

    # 2. Data Migration: Populate privacy_setting based on the old is_public column
    # Ensure trees table exists and has is_public column for this to work.
    # This assumes is_public was a Boolean column.
    op.execute("UPDATE trees SET privacy_setting = CASE WHEN is_public = TRUE THEN 'PUBLIC' ELSE 'PRIVATE' END")
    
    # 3. Make privacy_setting non-nullable and set server default
    # The default value 'PRIVATE' for TreePrivacySettingEnum.PRIVATE.value might be specific.
    # Using sa.text for server_default is often more portable for enums.
    op.alter_column('trees', 'privacy_setting', nullable=False, server_default='PRIVATE')

    # 4. Drop the old is_public column
    op.drop_column('trees', 'is_public')


def downgrade():
    # 1. Add back the is_public column
    op.add_column('trees', sa.Column('is_public', sa.Boolean(), server_default=sa.false(), nullable=True)) # Nullable first

    # 2. Data Migration: Populate is_public based on privacy_setting
    # This assumes privacy_setting exists.
    op.execute("UPDATE trees SET is_public = CASE WHEN privacy_setting = 'PUBLIC' THEN TRUE ELSE FALSE END")

    # Make is_public non-nullable if it was originally
    op.alter_column('trees', 'is_public', nullable=False, server_default=sa.false())


    # 3. Drop the privacy_setting column
    op.drop_column('trees', 'privacy_setting')
    
    # If the enum type was created by this migration (which it is, implicitly by sa.Enum usage),
    # it should be dropped. SQLAlchemy/Alembic usually handles enum types bound to columns.
    # If `create_type=False` was used in model, then DB type might not exist independently.
    # For safety, explicit drop if it was created globally:
    # tree_privacy_setting_enum.drop(op.get_bind(), checkfirst=True) 
    # However, typical Alembic enum usage with `create_type=False` in model means the type is tied to the column
    # and doesn't need separate dropping. If `create_type=True` (default) was used, then it would.
    # Given our model uses `create_type=False`, no explicit type drop is needed here.
    # The type `treeprivacysettingenum` will be dropped when the column using it is dropped if no other columns use it.
    # Or, if it's a user-defined type in PostgreSQL, it might need `DROP TYPE treeprivacysettingenum;`
    # For now, assuming standard Alembic behavior with enums tied to columns.
    # If there are issues, an explicit `op.execute("DROP TYPE IF EXISTS treeprivacysettingenum;")` might be needed.
    # This is safer if the type might linger.
    # Let's check if the type `treeprivacysettingenum` exists before trying to drop it.
    # This is more complex than typical Alembic, usually it handles its own enum types.
    # Given the `name` parameter in `sa.Enum`, Alembic might create it.
    # A more robust way to handle enums is to use `postgresql.ENUM` directly for PG.
    # Since the model used `SQLAlchemyEnum(TreePrivacySettingEnum, name="treeprivacysettingenum", create_type=False)`,
    # it implies the type might not be managed by SQLAlchemy at the DB level directly as a standalone type.
    # However, if `op.add_column` with `sa.Enum` creates the type, then dropping the column should handle it.
    # Let's ensure the type itself is dropped if it exists
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS treeprivacysettingenum;")
    # For other dialects, this might not be necessary or might have different syntax.
    # This is a common pattern for PostgreSQL when enums are created by SA/Alembic.
