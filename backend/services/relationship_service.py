# backend/services/relationship_service.py
import uuid
import structlog
from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_ # For filtering
from flask import abort

from ..models import Relationship, Person, RelationshipTypeEnum
from ..utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from ..config import PAGINATION_DEFAULTS, DEFAULT_PAGE, DEFAULT_PAGE_SIZE
# from opentelemetry import trace

# tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)

def get_all_relationships_db(db: DBSession,
                               tree_id: uuid.UUID,
                               page: int = DEFAULT_PAGE,
                               per_page: int = DEFAULT_PAGE_SIZE,
                               sort_by: Optional[str] = "created_at",
                               sort_order: Optional[str] = "desc",
                               filters: Optional[Dict[str, Any]] = None
                               ) -> Dict[str, Any]:
    """Fetches a paginated list of relationships for a given tree."""
    logger.info("Fetching all relationships for tree", tree_id=tree_id, page=page, per_page=per_page, filters=filters)
    try:
        query = db.query(Relationship).filter(Relationship.tree_id == tree_id)

        if filters:
            if 'person_id' in filters and filters['person_id']:
                try:
                    person_uuid = uuid.UUID(str(filters['person_id']))
                    query = query.filter(or_(Relationship.person1_id == person_uuid, Relationship.person2_id == person_uuid))
                except ValueError:
                    abort(400, description="Invalid person_id format for filtering relationships.")
            
            if 'relationship_type' in filters and filters['relationship_type']:
                try:
                    rel_type_enum = RelationshipTypeEnum(str(filters['relationship_type']))
                    query = query.filter(Relationship.relationship_type == rel_type_enum)
                except ValueError:
                    logger.warning(f"Invalid relationship_type filter: {filters['relationship_type']}. Ignoring filter.")
                    # Or abort(400, description=f"Invalid relationship_type: {filters['relationship_type']}")

        if not hasattr(Relationship, sort_by or ""):
            logger.warning(f"Invalid sort_by column '{sort_by}' for Relationship. Defaulting to 'created_at'.")
            sort_by = "created_at"

        return paginate_query(query, Relationship, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e:
        logger.error("Database error fetching all relationships for tree.", tree_id=tree_id, exc_info=True)
        _handle_sqlalchemy_error(e, f"fetching all relationships for tree {tree_id}", db)
    except HTTPException: # Re-raise aborts from filters
        raise
    except Exception as e:
        logger.error("Unexpected error fetching all relationships for tree.", tree_id=tree_id, exc_info=True)
        abort(500, "An unexpected error occurred while fetching relationships.")
    return {} # Should be unreachable

def get_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID) -> Dict[str, Any]:
    """Fetches a single relationship by ID within a specific tree."""
    logger.info("Fetching relationship details", relationship_id=relationship_id, tree_id=tree_id)
    relationship = _get_or_404(db, Relationship, relationship_id, tree_id=tree_id)
    return relationship.to_dict()

def create_relationship_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, rel_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new relationship in the database for a given tree."""
    logger.info("Attempting to create new relationship", user_id=user_id, tree_id=tree_id, data_keys=list(rel_data.keys()))

    p1_id_str = rel_data.get('person1_id')
    p2_id_str = rel_data.get('person2_id')
    rel_type_str = rel_data.get('relationship_type')
    errors = {}

    if not p1_id_str: errors['person1_id'] = "person1_id is required."
    if not p2_id_str: errors['person2_id'] = "person2_id is required."
    if not rel_type_str: errors['relationship_type'] = "relationship_type is required."
    if errors:
        abort(400, description={"message": "Validation failed", "details": errors})

    if p1_id_str == p2_id_str:
        abort(400, description="Cannot create a relationship between a person and themselves.")

    try:
        person1_id = uuid.UUID(p1_id_str)
        person2_id = uuid.UUID(p2_id_str)
        relationship_type = RelationshipTypeEnum(rel_type_str)
    except ValueError as e: # Catches invalid UUID or Enum
        abort(400, description=f"Invalid input format: {e}")

    # Verify persons exist in the tree
    _get_or_404(db, Person, person1_id, tree_id=tree_id)
    _get_or_404(db, Person, person2_id, tree_id=tree_id)

    start_date, end_date = None, None
    if rel_data.get('start_date'):
        try: start_date = date.fromisoformat(rel_data['start_date'])
        except ValueError: abort(400, description={"message": "Validation failed", "details": {"start_date": "Invalid date format (YYYY-MM-DD)."}})
    if rel_data.get('end_date'):
        try: end_date = date.fromisoformat(rel_data['end_date'])
        except ValueError: abort(400, description={"message": "Validation failed", "details": {"end_date": "Invalid date format (YYYY-MM-DD)."}})
    
    if start_date and end_date and end_date < start_date:
         abort(400, description={"message": "Validation failed", "details": {"date_comparison": "End date cannot be before start date."}})

    try:
        new_relationship = Relationship(
            tree_id=tree_id, created_by=user_id,
            person1_id=person1_id, person2_id=person2_id,
            relationship_type=relationship_type,
            start_date=start_date, end_date=end_date,
            certainty_level=rel_data.get('certainty_level'),
            custom_attributes=rel_data.get('custom_attributes', {}),
            notes=rel_data.get('notes')
        )
        db.add(new_relationship)
        db.commit()
        db.refresh(new_relationship)
        logger.info("Relationship created successfully", rel_id=new_relationship.id, tree_id=tree_id)
        return new_relationship.to_dict()
    except IntegrityError as e: # Catch unique constraint (e.g. uq_relationship_key_fields)
        logger.warning("Relationship creation failed: Integrity constraint violation.", tree_id=tree_id, exc_info=False)
        _handle_sqlalchemy_error(e, "creating relationship (integrity)", db)
    except SQLAlchemyError as e:
        logger.error("Database error during relationship creation.", tree_id=tree_id, exc_info=True)
        _handle_sqlalchemy_error(e, "creating relationship", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during relationship creation.", tree_id=tree_id, exc_info=True)
        abort(500, description="An unexpected error occurred during relationship creation.")
    return {} # Should be unreachable


def update_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID, rel_data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates an existing relationship in the database."""
    logger.info("Attempting to update relationship", rel_id=relationship_id, tree_id=tree_id, data_keys=list(rel_data.keys()))
    relationship = _get_or_404(db, Relationship, relationship_id, tree_id=tree_id)
    
    validation_errors = {}
    allowed_fields = [
        'person1_id', 'person2_id', 'relationship_type', 'start_date', 'end_date',
        'certainty_level', 'custom_attributes', 'notes'
    ]

    for field, value in rel_data.items():
        if field not in allowed_fields:
            logger.warning(f"Attempt to update unallowed field '{field}' for relationship {relationship_id}.")
            continue
        try:
            if field in ['person1_id', 'person2_id']:
                person_uuid = uuid.UUID(str(value)) if value else None
                if person_uuid: _get_or_404(db, Person, person_uuid, tree_id=tree_id) # Check person exists in tree
                setattr(relationship, field, person_uuid)
            elif field == 'relationship_type':
                setattr(relationship, field, RelationshipTypeEnum(value) if value else None)
            elif field in ['start_date', 'end_date']:
                setattr(relationship, field, date.fromisoformat(str(value)) if value else None)
            elif field == 'certainty_level':
                if value is not None and (not isinstance(value, int) or not (0 <= value <= 5)):
                     validation_errors[field] = "Certainty level must be an integer between 0 and 5."
                else: setattr(relationship, field, value)
            elif field == 'custom_attributes':
                if not isinstance(value, dict): validation_errors[field] = "Custom attributes must be a dictionary."
                else: setattr(relationship, field, value)
            else: # notes
                setattr(relationship, field, value)
        except ValueError as e:
            validation_errors[field] = f"Invalid value or format for {field}: {e}"
        except HTTPException: raise # Re-raise 404 from _get_or_404
        except Exception as e:
            logger.error(f"Unexpected error processing field {field} for relationship update.", exc_info=True)
            validation_errors[field] = f"Unexpected error processing {field}."

    if validation_errors:
         logger.warning("Relationship update failed: Validation errors.", rel_id=relationship_id, errors=validation_errors)
         abort(400, description={"message": "Validation failed", "details": validation_errors})

    if relationship.person1_id == relationship.person2_id:
          abort(400, description="Cannot have a relationship where person1 and person2 are the same.")
    if relationship.start_date and relationship.end_date and relationship.end_date < relationship.start_date:
        abort(400, description="End date cannot be before start date.")
    
    try:
        db.commit()
        db.refresh(relationship)
        logger.info("Relationship updated successfully", rel_id=relationship.id, tree_id=tree_id)
        return relationship.to_dict()
    except SQLAlchemyError as e:
        logger.error("Database error during relationship update.", rel_id=relationship_id, exc_info=True)
        _handle_sqlalchemy_error(e, f"updating relationship ID {relationship_id}", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during relationship update.", rel_id=relationship_id, exc_info=True)
        abort(500, description="An unexpected error occurred during relationship update.")
    return {} # Should be unreachable

def delete_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    """Deletes a relationship from the database."""
    logger.info("Attempting to delete relationship", rel_id=relationship_id, tree_id=tree_id)
    relationship = _get_or_404(db, Relationship, relationship_id, tree_id=tree_id)
    try:
        db.delete(relationship)
        db.commit()
        logger.info("Relationship deleted successfully", rel_id=relationship_id, tree_id=tree_id)
        return True
    except SQLAlchemyError as e:
        logger.error("Database error during relationship deletion.", rel_id=relationship_id, exc_info=True)
        _handle_sqlalchemy_error(e, f"deleting relationship ID {relationship_id}", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during relationship deletion.", rel_id=relationship_id, exc_info=True)
        abort(500, description="An unexpected error occurred during relationship deletion.")
    return False # Should be unreachable
