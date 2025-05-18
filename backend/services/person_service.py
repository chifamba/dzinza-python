# backend/services/person_service.py
# backend/services/person_service.py
"""Provides service functions for managing Person objects in the database."""

import uuid
import structlog
from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_ # For name search
from flask import abort

from models import Person, PrivacyLevelEnum
from utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
import config as app_config_module

logger = structlog.get_logger(__name__)

def get_all_people_db(db: DBSession,
                        tree_id: uuid.UUID,
                        page: int = -1,
                        per_page: int = -1,
                        sort_by: Optional[str] = "last_name",
                        sort_order: Optional[str] = "asc",
                        filters: Optional[Dict[str, Any]] = None
                        ) -> Dict[str, Any]: # type: ignore
    # Enhance the existing docstring
    """
    Fetches a paginated list of people for a given tree.

    Args:
        db: The SQLAlchemy database session.
        tree_id: The UUID of the tree to fetch people from.
        page: The page number for pagination (defaults to config).
        per_page: The number of items per page for pagination (defaults to config).
        sort_by: The field to sort by (defaults to 'last_name').
        sort_order: The sort order ('asc' or 'desc', defaults to 'asc').
        filters: An optional dictionary of filters (e.g., {'is_living': True, 'name_contains': 'John'}).

    Returns:
    """Fetches a paginated list of people for a given tree."""
    cfg_pagination = app_config_module.config.PAGINATION_DEFAULTS
    if page == -1: page = cfg_pagination["page"]
    if per_page == -1: per_page = cfg_pagination["per_page"]

    logger.info("Fetching people for tree", tree_id=tree_id, page=page, per_page=per_page, sort_by=sort_by, filters=filters)
    try:
        query = db.query(Person).filter(Person.tree_id == tree_id)

        if filters:
            if 'is_living' in filters and isinstance(filters['is_living'], bool):
                query = query.filter(Person.is_living == filters['is_living'])
            if 'gender' in filters and filters['gender']:
                query = query.filter(Person.gender.ilike(f"%{filters['gender']}%"))
            if 'name_contains' in filters and filters['name_contains']:
                term = f"%{filters['name_contains']}%"
                query = query.filter(
                    or_(Person.first_name.ilike(term), Person.last_name.ilike(term),
                        Person.nickname.ilike(term), Person.maiden_name.ilike(term))
                )
        
        if not hasattr(Person, sort_by or ""):
            logger.warning(f"Invalid sort_by column '{sort_by}' for Person. Defaulting to 'last_name'.")
            sort_by = "last_name"

        return paginate_query(query, Person, page, per_page, cfg_pagination["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"fetching people for tree {tree_id}", db)
    except Exception as e:
        logger.error("Unexpected error fetching people.", tree_id=tree_id, exc_info=True)
        abort(500, "Error fetching people.")
    return {}

def get_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID) -> Dict[str, Any]:
    """
    Fetches the details of a specific person by ID within a given tree.

    Args:
        db: The SQLAlchemy database session.
        person_id: The UUID of the person to fetch.
        tree_id: The UUID of the tree the person belongs to.

    Returns:
        A dictionary representation of the Person object.

    Raises:
        HTTPException: If the person is not found or a database error occurs.
    """
    logger.info("Fetching person details", person_id=person_id, tree_id=tree_id)
    person = _get_or_404(db, Person, person_id, tree_id=tree_id)
    return person.to_dict()

def create_person_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a new person record in the database for a given tree.

    Args:
        db: The SQLAlchemy database session.
        user_id: The UUID of the user creating the person.
    person_name_log = f"{person_data.get('first_name', '')} {person_data.get('last_name', '')}".strip()
    logger.info("Creating new person", user_id=user_id, tree_id=tree_id, person_name=person_name_log)

    if not person_data.get('first_name'):
        abort(400, description={"message": "Validation failed", "details": {"first_name": "First name is required."}})

    errors = {}
    birth_date_str = person_data.get('birth_date'); death_date_str = person_data.get('death_date')
    birth_date, death_date = None, None

    if birth_date_str:
        try: birth_date = date.fromisoformat(birth_date_str)
        except ValueError: errors['birth_date'] = "Invalid date format (YYYY-MM-DD)."
    if death_date_str:
        try: death_date = date.fromisoformat(death_date_str)
        except ValueError: errors['death_date'] = "Invalid date format (YYYY-MM-DD)."
    if birth_date and death_date and death_date < birth_date:
        errors['date_comparison'] = "Death date cannot be before birth date."
    gender = person_data.get('gender')
    if gender and str(gender).lower() not in ['male', 'female', 'other', 'unknown', '']:
         errors['gender'] = "Invalid gender. Allowed: male, female, other, unknown, or empty."
    privacy_level_str = person_data.get('privacy_level', PrivacyLevelEnum.inherit.value)
    try: privacy_level_enum = PrivacyLevelEnum(privacy_level_str)
    except ValueError: errors['privacy_level'] = f"Invalid privacy level: {privacy_level_str}."

    if errors:
        logger.warning("Person creation validation errors.", errors=errors, tree_id=tree_id)
        abort(400, description={"message": "Validation failed", "details": errors})

    try:
        new_person = Person(
            tree_id=tree_id, created_by=user_id, first_name=person_data['first_name'],
            middle_names=person_data.get('middle_names'), last_name=person_data.get('last_name'),
            maiden_name=person_data.get('maiden_name'), nickname=person_data.get('nickname'),
            gender=gender if gender else None, birth_date=birth_date,
            birth_date_approx=person_data.get('birth_date_approx', False), birth_place=person_data.get('birth_place'),
            death_date=death_date, death_date_approx=person_data.get('death_date_approx', False),
            death_place=person_data.get('death_place'), burial_place=person_data.get('burial_place'),
            privacy_level=privacy_level_enum, is_living=person_data.get('is_living'),
            notes=person_data.get('notes'), custom_attributes=person_data.get('custom_attributes', {})
        )
        if new_person.is_living is None: new_person.is_living = new_person.death_date is None
        db.add(new_person); db.commit(); db.refresh(new_person)
        logger.info("Person created.", person_id=new_person.id, tree_id=tree_id)
        return new_person.to_dict()
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "creating person", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error creating person.", tree_id=tree_id, exc_info=True)
        abort(500, "Error creating person.")
    return {}

def update_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates an existing person's record in the database.

    Args:
        db: The SQLAlchemy database session.
        person_id: The UUID of the person to update.
        tree_id: The UUID of the tree the person belongs to.
        person_data: A dictionary containing the fields to update.

    Returns:
        A dictionary representation of the updated Person object.

    Raises:
    logger.info("Updating person", person_id=person_id, tree_id=tree_id, data_keys=list(person_data.keys()))
    person = _get_or_404(db, Person, person_id, tree_id=tree_id)
    
    validation_errors = {}; allowed_fields = [
        'first_name', 'middle_names', 'last_name', 'maiden_name', 'nickname', 'gender',
        'birth_date', 'birth_date_approx', 'birth_place', 'death_date', 'death_date_approx',
        'death_place', 'burial_place', 'privacy_level', 'is_living', 'notes', 'custom_attributes']
    for field, value in person_data.items():
        if field not in allowed_fields: continue
        try:
            if field in ['birth_date', 'death_date']: setattr(person, field, date.fromisoformat(value) if value else None)
            elif field == 'gender':
                if value is not None and str(value).lower() not in ['male', 'female', 'other', 'unknown', '']:
                     validation_errors[field] = "Invalid gender value."
                else: setattr(person, field, value if value else None)
            elif field == 'privacy_level': setattr(person, field, PrivacyLevelEnum(value) if value else person.privacy_level)
            elif field == 'custom_attributes':
                 if not isinstance(value, dict): validation_errors[field] = "Custom attributes must be a dict."
                 else: setattr(person, field, value)
            elif field in ['is_living', 'birth_date_approx', 'death_date_approx']:
                 if not isinstance(value, bool): validation_errors[field] = f"{field} must be boolean."
                 else: setattr(person, field, value)
            else: setattr(person, field, value)
        except ValueError as e: validation_errors[field] = f"Invalid value for {field}: {e}"
        except Exception as e: logger.error(f"Error processing field {field} for person update.", exc_info=True); validation_errors[field] = "Error processing field."
    if validation_errors: abort(400, description={"message": "Validation failed", "details": validation_errors})
    if person.birth_date and person.death_date and person.death_date < person.birth_date:
        abort(400, description={"message": "Validation failed", "details": {"date_comparison": "Death date before birth date."}})
    if 'is_living' not in person_data and ('death_date' in person_data or 'birth_date' in person_data):
         person.is_living = person.death_date is None
    try:
        db.commit(); db.refresh(person)
        logger.info("Person updated.", person_id=person.id, tree_id=tree_id)
        return person.to_dict()
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, f"updating person {person_id}", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error updating person.", person_id=person_id, exc_info=True)
        abort(500, "Error updating person.")
    return {}

def delete_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    """
    Deletes a person record from the database.

    Args:
        db: The SQLAlchemy database session.
        person_id: The UUID of the person to delete.
        tree_id: The UUID of the tree the person belongs to.

    Returns:
        True if deletion was successful.

    Raises:
    logger.info("Deleting person", person_id=person_id, tree_id=tree_id)
    person = _get_or_404(db, Person, person_id, tree_id=tree_id)
    try:
        db.delete(person); db.commit()
        logger.info("Person deleted.", person_id=person_id, tree_id=tree_id)
        return True
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, f"deleting person {person_id}", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error deleting person.", person_id=person_id, exc_info=True)
        abort(500, "Error deleting person.")
    return False
