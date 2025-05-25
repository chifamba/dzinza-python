# backend/services/relationship_service.py
import uuid
import structlog
from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_
from flask import abort

from models import Relationship, Person, RelationshipTypeEnum, PersonTreeAssociation # Added PersonTreeAssociation
from utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
import config as app_config_module
# Import for get_relationships_for_tree_db
from services.person_service import get_all_people_db as get_persons_in_tree_db


logger = structlog.get_logger(__name__)

# For future use: Map of relationship types to their inverses.
# Not used for automatic creation in the current implementation.
INVERSE_RELATIONSHIP_MAP = {
    RelationshipTypeEnum.biological_parent: RelationshipTypeEnum.biological_child,
    RelationshipTypeEnum.adoptive_parent: RelationshipTypeEnum.adoptive_child,
    RelationshipTypeEnum.step_parent: RelationshipTypeEnum.step_child,
    RelationshipTypeEnum.foster_parent: RelationshipTypeEnum.foster_child,
    RelationshipTypeEnum.guardian: None,  # Guardian relationship might not have a direct inverse in this list
    RelationshipTypeEnum.biological_child: RelationshipTypeEnum.biological_parent,
    RelationshipTypeEnum.adoptive_child: RelationshipTypeEnum.adoptive_parent,
    RelationshipTypeEnum.step_child: RelationshipTypeEnum.step_parent,
    RelationshipTypeEnum.foster_child: RelationshipTypeEnum.foster_parent,
    # Symmetrical relationships map to themselves
    RelationshipTypeEnum.spouse_current: RelationshipTypeEnum.spouse_current,
    RelationshipTypeEnum.spouse_former: RelationshipTypeEnum.spouse_former,
    RelationshipTypeEnum.partner: RelationshipTypeEnum.partner,
    RelationshipTypeEnum.sibling_full: RelationshipTypeEnum.sibling_full,
    RelationshipTypeEnum.sibling_half: RelationshipTypeEnum.sibling_half,
    RelationshipTypeEnum.sibling_step: RelationshipTypeEnum.sibling_step,
    RelationshipTypeEnum.sibling_adoptive: RelationshipTypeEnum.sibling_adoptive,
    RelationshipTypeEnum.other: RelationshipTypeEnum.other, # 'other' is symmetrical by default
}


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
    logger.info("Fetching relationship", relationship_id=relationship_id) # Removed tree_id from log
    relationship = _get_or_404(db, Relationship, relationship_id) # Fetch globally
    return relationship.to_dict()

def create_relationship_db(db: DBSession, user_id: uuid.UUID, rel_data: Dict[str, Any]) -> Dict[str, Any]:
    # Removed tree_id from parameters
    logger.info("Creating relationship", user_id=user_id, data_keys=list(rel_data.keys()))
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
    # Validate persons globally
    _get_or_404(db, Person, person1_id); _get_or_404(db, Person, person2_id)
    start_date, end_date = None, None
    if rel_data.get('start_date'):
        try: start_date = date.fromisoformat(rel_data['start_date'])
        except ValueError: abort(400, {"message": "Validation failed", "details": {"start_date": "Invalid date format."}})
    if rel_data.get('end_date'):
        try: end_date = date.fromisoformat(rel_data['end_date'])
        except ValueError: abort(400, {"message": "Validation failed", "details": {"end_date": "Invalid date format."}})
    if start_date and end_date and end_date < start_date: abort(400, {"message": "Validation failed", "details": {"date_comparison": "End date before start."}})
    try:
        new_rel = Relationship( # tree_id removed
            created_by=user_id, person1_id=person1_id, person2_id=person2_id,
            relationship_type=relationship_type, start_date=start_date, end_date=end_date,
            certainty_level=rel_data.get('certainty_level'), custom_attributes=rel_data.get('custom_attributes', {}),
            notes=rel_data.get('notes'), location=rel_data.get('location'))
        db.add(new_rel); db.commit(); db.refresh(new_rel)
        logger.info("Relationship created.", rel_id=new_rel.id) # Removed tree_id from log
        return new_rel.to_dict()
    except IntegrityError as e: _handle_sqlalchemy_error(e, "creating relationship (integrity)", db)
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "creating relationship", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error creating relationship.", exc_info=True) # Removed tree_id from log
        abort(500, "Error creating relationship.")
    return {}

def update_relationship_db(db: DBSession, relationship_id: uuid.UUID, rel_data: Dict[str, Any]) -> Dict[str, Any]:
    # Removed tree_id from parameters
    logger.info("Updating relationship", rel_id=relationship_id, data_keys=list(rel_data.keys()))
    relationship = _get_or_404(db, Relationship, relationship_id) # Fetch globally
    # Authorization to update a relationship would typically depend on user's rights to edit EITHER person involved,
    # or specific rights to the relationship type, or admin rights. This is not handled here yet.

    validation_errors = {}; allowed_fields = ['person1_id', 'person2_id', 'relationship_type', 'start_date', 'end_date',
        'certainty_level', 'custom_attributes', 'notes', 'location']
    for field, value in rel_data.items():
        if field not in allowed_fields: continue
        try:
            if field in ['person1_id', 'person2_id']:
                person_uuid = uuid.UUID(str(value)) if value else None
                if person_uuid: _get_or_404(db, Person, person_uuid) # Validate globally
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

def get_relationships_for_person_db(db: DBSession,
                                    person_id: uuid.UUID,
                                    page: int = -1, per_page: int = -1,
                                    sort_by: Optional[str] = "created_at",
                                    sort_order: Optional[str] = "desc",
                                    filters: Optional[Dict[str, Any]] = None
                                    ) -> Dict[str, Any]:
    """Fetches all global relationships for a given person."""
    cfg_pagination = app_config_module.config.PAGINATION_DEFAULTS
    if page == -1: page = cfg_pagination["page"]
    if per_page == -1: per_page = cfg_pagination["per_page"]

    logger.info("Fetching all relationships for person", person_id=person_id, page=page, per_page=per_page, filters=filters)
    
    # Ensure person exists globally
    _get_or_404(db, Person, person_id)

    try:
        query = db.query(Relationship).filter(
            or_(Relationship.person1_id == person_id, Relationship.person2_id == person_id)
        )

        if filters:
            # Example filter: by relationship type
            if 'relationship_type' in filters and filters['relationship_type']:
                try:
                    query = query.filter(Relationship.relationship_type == RelationshipTypeEnum(str(filters['relationship_type'])))
                except ValueError:
                    logger.warning(f"Invalid relationship_type filter: {filters['relationship_type']}. Ignoring.")
            # Example filter: by other person involved (if a specific other person is provided)
            if 'other_person_id' in filters and filters['other_person_id']:
                try:
                    other_person_uuid = uuid.UUID(str(filters['other_person_id']))
                    # Ensure this other person also exists globally
                    _get_or_404(db, Person, other_person_uuid)
                    query = query.filter(
                        or_(
                            (Relationship.person1_id == person_id) & (Relationship.person2_id == other_person_uuid),
                            (Relationship.person1_id == other_person_uuid) & (Relationship.person2_id == person_id)
                        )
                    )
                except ValueError:
                    abort(400, "Invalid other_person_id format for filter.")
                except HTTPException: # Catch 404 if other_person_id does not exist
                    logger.warning(f"Other person_id {filters['other_person_id']} not found for filtering. Relationship might not exist.")
                    # Depending on desired behavior, could return empty or just ignore this part of the filter.
                    # For now, if other_person_id is specified but not found, the query will likely yield no results if that person was essential.

        if not hasattr(Relationship, sort_by or ""):
            logger.warning(f"Invalid sort_by '{sort_by}' for Relationship. Defaulting to 'created_at'.")
            sort_by = "created_at"
            
        return paginate_query(query, Relationship, page, per_page, cfg_pagination["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"fetching relationships for person {person_id}", db)
    except HTTPException: # Re-raise aborts (e.g. from _get_or_404 if other_person_id not found)
        raise
    except Exception as e:
        logger.error("Unexpected error fetching relationships for person.", person_id=person_id, exc_info=True)
        abort(500, "Error fetching relationships for person.")
    return {}

def delete_relationship_db(db: DBSession, relationship_id: uuid.UUID) -> bool:
    # Removed tree_id from parameters
    logger.info("Deleting relationship", rel_id=relationship_id)
    relationship = _get_or_404(db, Relationship, relationship_id) # Fetch globally
    # Authorization to delete a relationship would be similar to updating.

    try:
        db.delete(relationship); db.commit()
        logger.info("Relationship deleted.", rel_id=relationship_id) # Removed tree_id from log
        return True
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, f"deleting relationship {relationship_id}", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error deleting relationship.", rel_id=relationship_id, exc_info=True)
        abort(500, "Error deleting relationship.")
    return False
