"""globalize_person_event_relationship_models

Revision ID: globalize_person_models
Revises: 29bd3cc00267
Create Date: 2024-08-07 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'globalize_person_models'
down_revision = '29bd3cc00267'
branch_labels = None
depends_on = None


def upgrade():
    # ### Manual Alembic commands ###

    # 1. Create PersonTreeAssociation table
    op.create_table('person_tree_association',
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tree_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], name=op.f('fk_person_tree_association_person_id_people'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tree_id'], ['trees.id'], name=op.f('fk_person_tree_association_tree_id_trees'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('person_id', 'tree_id', name=op.f('pk_person_tree_association'))
    )
    
    # For dropping columns with FKs, it's safer to drop the FK constraint first if its name is known.
    # Alembic's batch mode can also handle this more robustly.
    # Assuming conventional naming for FK constraints if not using batch mode.
    # Example: fk_people_tree_id_trees (table_column_target_column)

    with op.batch_alter_table('people', schema=None) as batch_op:
        # Attempt to drop a conventionally named FK if it exists.
        # If the FK name is different or doesn't exist, this might be skipped or error depending on DB.
        # For a robust solution, the exact name is needed.
        try:
            batch_op.drop_constraint('fk_people_tree_id_trees', type_='foreignkey')
        except Exception as e:
            print(f"Skipping drop_constraint fk_people_tree_id_trees: {e}")
        batch_op.drop_column('tree_id')

    with op.batch_alter_table('events', schema=None) as batch_op:
        try:
            batch_op.drop_constraint('fk_events_tree_id_trees', type_='foreignkey')
        except Exception as e:
            print(f"Skipping drop_constraint fk_events_tree_id_trees: {e}")
        batch_op.drop_column('tree_id')

    with op.batch_alter_table('relationships', schema=None) as batch_op:
        # The unique constraint `uq_relationship_key_fields` needs to be dropped before tree_id column
        # and then recreated without tree_id.
        try:
            batch_op.drop_constraint('uq_relationship_key_fields', type_='unique')
        except Exception as e:
            print(f"Skipping drop_constraint uq_relationship_key_fields: {e}")
        
        try:
            batch_op.drop_constraint('fk_relationships_tree_id_trees', type_='foreignkey')
        except Exception as e:
            print(f"Skipping drop_constraint fk_relationships_tree_id_trees: {e}")
        batch_op.drop_column('tree_id')
        batch_op.create_unique_constraint(op.f('uq_relationship_key_fields'), ['person1_id', 'person2_id', 'relationship_type'])


    with op.batch_alter_table('media', schema=None) as batch_op:
        batch_op.alter_column('tree_id',
               existing_type=postgresql.UUID(as_uuid=True),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### Manual Alembic commands ###

    with op.batch_alter_table('media', schema=None) as batch_op:
        batch_op.alter_column('tree_id',
               existing_type=postgresql.UUID(as_uuid=True),
               nullable=False) # Data migration might be needed if NULLs exist

    with op.batch_alter_table('relationships', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tree_id', postgresql.UUID(as_uuid=True), autoincrement=False, nullable=True)) 
        # In a real downgrade, you'd need a strategy to populate this tree_id. Here, making it nullable.
        # Then, after data population, it could be altered to nullable=False.
        batch_op.create_foreign_key(op.f('fk_relationships_tree_id_trees'), 'trees', ['tree_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_constraint(op.f('uq_relationship_key_fields'), type_='unique')
        batch_op.create_unique_constraint(op.f('uq_relationship_key_fields_downgrade'), ['tree_id', 'person1_id', 'person2_id', 'relationship_type'])
        # Note: Constraint names should be unique. If uq_relationship_key_fields was the original name, 
        # it might need a different name for the downgrade version if the original still exists due to partial failure.
        # Using op.f() helps generate consistent names.

    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tree_id', postgresql.UUID(as_uuid=True), autoincrement=False, nullable=True))
        batch_op.create_foreign_key(op.f('fk_events_tree_id_trees'), 'trees', ['tree_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('people', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tree_id', postgresql.UUID(as_uuid=True), autoincrement=False, nullable=True))
        batch_op.create_foreign_key(op.f('fk_people_tree_id_trees'), 'trees', ['tree_id'], ['id'], ondelete='CASCADE')

    op.drop_table('person_tree_association')

    # ### end Alembic commands ###
