# backend/services/relationship_service.py
import uuid
import structlog
from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_
from flask import abort

from backend.models import Relationship, Person, RelationshipTypeEnum
from backend.utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from backend import config as app_config_module

logger = structlog.get_logger(__name__)

def get_all_relationships_db(db: DBSession,
                               tree_id: uuid.UUID,
                               page: int = -1, per_page: int = -1,
                               sort_by: Optional[str] = "created_at",
                               sort_order: Optional[str] = "desc",
                               filters: Optional[Dict[str, Any]] = None
                               ) -> Dict[str, Any]:
    cfg_pagination = app_config_module.config.PAGINATION_DEFAULTS
    if page == -1: page = cfg_pagination["page"]
    if per_page == -1: per_page = cfg_pagination["per_page"]

    logger.info("Fetching relationships for tree", tree_id=tree_id, page=page, per_page=per_page, filters=filters)
    try:
        query = db.query(Relationship).filter(Relationship.tree_id == tree_id)
        if filters:
            if 'person_id' in filters and filters['person_id']:
                try: person_uuid = uuid.UUID(str(filters['person_id']))
                except ValueError: abort(400, "Invalid person_id format for filter.")
                query = query.filter(or_(Relationship.person1_id == person_uuid, Relationship.person2_id == person_uuid))
            if 'relationship_type' in filters and filters['relationship_type']:
                try: query = query.filter(Relationship.relationship_type == RelationshipTypeEnum(str(filters['relationship_type'])))
                except ValueError: logger.warning(f"Invalid relationship_type filter: {filters['relationship_type']}. Ignoring.")
        if not hasattr(Relationship, sort_by or ""):
            logger.warning(f"Invalid sort_by '{sort_by}' for Relationship. Defaulting to 'created_at'.")
            sort_by = "created_at"
        return paginate_query(query, Relationship, page, per_page, cfg_pagination["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, f"fetching relationships for tree {tree_id}", db)
    except HTTPException: raise
    except Exception as e:
        logger.error("Unexpected error fetching relationships.", tree_id=tree_id, exc_info=True)
        abort(500, "Error fetching relationships.")
    return {}

def get_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID) -> Dict[str, Any]:
    logger.info("Fetching relationship", relationship_id=relationship_id, tree_id=tree_id)
    relationship = _get_or_404(db, Relationship, relationship_id, tree_id=tree_id)
    return relationship.to_dict()

def create_relationship_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, rel_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Creating relationship", user_id=user_id, tree_id=tree_id, data_keys=list(rel_data.keys()))
    p1_id_str = rel_data.get('person1_id'); p2_id_str = rel_data.get('person2_id'); rel_type_str = rel_data.get('relationship_type')
    errors = {}
    if not p1_id_str: errors['person1_id'] = "Required."
    if not p2_id_str: errors['person2_id'] = "Required."
    if not rel_type_str: errors['relationship_type'] = "Required."
    if errors: abort(400, description={"message": "Validation failed", "details": errors})
    if p1_id_str == p2_id_str: abort(400, "Cannot relate a person to themselves.")
    try:
        person1_id = uuid.UUID(p1_id_str); person2_id = uuid.UUID(p2_id_str)
        relationship_type = RelationshipTypeEnum(rel_type_str)
    except ValueError as e: abort(400, f"Invalid input format: {e}")
    _get_or_404(db, Person, person1_id, tree_id=tree_id); _get_or_404(db, Person, person2_id, tree_id=tree_id)
    start_date, end_date = None, None
    if rel_data.get('start_date'):
        try: start_date = date.fromisoformat(rel_data['start_date'])
        except ValueError: abort(400, {"message": "Validation failed", "details": {"start_date": "Invalid date format."}})
    if rel_data.get('end_date'):
        try: end_date = date.fromisoformat(rel_data['end_date'])
        except ValueError: abort(400, {"message": "Validation failed", "details": {"end_date": "Invalid date format."}})
    if start_date and end_date and end_date < start_date: abort(400, {"message": "Validation failed", "details": {"date_comparison": "End date before start."}})
    try:
        location = rel_data.get('location')
        new_rel = Relationship(tree_id=tree_id, created_by=user_id, person1_id=person1_id, person2_id=person2_id,
            relationship_type=relationship_type, start_date=start_date, end_date=end_date,
            certainty_level=rel_data.get('certainty_level'), custom_attributes=rel_data.get('custom_attributes', {}),
            notes=rel_data.get('notes'), location=location)
        db.add(new_rel); db.commit(); db.refresh(new_rel)
        logger.info("Relationship created.", rel_id=new_rel.id, tree_id=tree_id)
        return new_rel.to_dict()
    except IntegrityError as e: _handle_sqlalchemy_error(e, "creating relationship (integrity)", db)
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "creating relationship", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error creating relationship.", tree_id=tree_id, exc_info=True)
        abort(500, "Error creating relationship.")
    return {}

def update_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID, rel_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Updating relationship", rel_id=relationship_id, tree_id=tree_id, data_keys=list(rel_data.keys()))
    relationship = _get_or_404(db, Relationship, relationship_id, tree_id=tree_id)
    validation_errors = {}; allowed_fields = ['person1_id', 'person2_id', 'relationship_type', 'start_date', 'end_date',
        'certainty_level', 'custom_attributes', 'notes', 'location']
    for field, value in rel_data.items():
        if field not in allowed_fields: continue
        try:
            if field in ['person1_id', 'person2_id']:
                person_uuid = uuid.UUID(str(value)) if value else None
                if person_uuid: _get_or_404(db, Person, person_uuid, tree_id=tree_id)
                setattr(relationship, field, person_uuid)
            elif field == 'relationship_type': setattr(relationship, field, RelationshipTypeEnum(value) if value else None)
            elif field in ['start_date', 'end_date']: setattr(relationship, field, date.fromisoformat(str(value)) if value else None)
            elif field == 'certainty_level':
                if value is not None and (not isinstance(value, int) or not (0 <= value <= 5)):
                     validation_errors[field] = "Certainty level must be int 0-5."
                else: setattr(relationship, field, value)
            elif field == 'custom_attributes':
                if not isinstance(value, dict): validation_errors[field] = "Custom attributes must be dict."
                else: setattr(relationship, field, value)
            else: setattr(relationship, field, value)
        except ValueError as e: validation_errors[field] = f"Invalid value for {field}: {e}"
        except HTTPException: raise
        except Exception as e: logger.error(f"Error processing field {field} for rel update.", exc_info=True); validation_errors[field] = "Error processing."
    if validation_errors: abort(400, {"message": "Validation failed", "details": validation_errors})
    if relationship.person1_id == relationship.person2_id: abort(400, "Persons in relationship cannot be same.")
    if relationship.start_date and relationship.end_date and relationship.end_date < relationship.start_date:
        abort(400, "End date cannot be before start date.")
    try:
        db.commit(); db.refresh(relationship)
        logger.info("Relationship updated.", rel_id=relationship.id, tree_id=tree_id)
        return relationship.to_dict()
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, f"updating relationship {relationship_id}", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error updating relationship.", rel_id=relationship_id, exc_info=True)
        abort(500, "Error updating relationship.")
    return {}

def delete_relationship_db(db: DBSession, relationship_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    logger.info("Deleting relationship", rel_id=relationship_id, tree_id=tree_id)
    relationship = _get_or_404(db, Relationship, relationship_id, tree_id=tree_id)
    try:
        db.delete(relationship); db.commit()
        logger.info("Relationship deleted.", rel_id=relationship_id, tree_id=tree_id)
        return True
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, f"deleting relationship {relationship_id}", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error deleting relationship.", rel_id=relationship_id, exc_info=True)
        abort(500, "Error deleting relationship.")
    return False
