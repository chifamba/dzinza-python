# backend/services/person_service.py
import uuid
import structlog
from datetime import date
from typing import Dict, Any, Optional, List # Ensure List is also imported if used by paginate_query
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
from flask import abort
from werkzeug.exceptions import HTTPException

# Absolute imports from the app root
from backend.models import Person, PrivacyLevelEnum
from backend.utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from backend import config as app_config_module

logger = structlog.get_logger(__name__)

def get_all_people_db(db: DBSession,
                        tree_id: uuid.UUID,
                        page: int = -1, # Default to trigger config lookup
                        per_page: int = -1, # Default to trigger config lookup
                        sort_by: Optional[str] = "last_name",
                        sort_order: Optional[str] = "asc",
                        filters: Optional[Dict[str, Any]] = None
                        ) -> Dict[str, Any]:
    """
    Fetches a paginated list of people for a given tree.
    Correctly indented docstring.
    """
    cfg_pagination = app_config_module.config.PAGINATION_DEFAULTS
    # Use default from config if page/per_page are sentinel -1
    current_page = page if page != -1 else cfg_pagination["page"]
    current_per_page = per_page if per_page != -1 else cfg_pagination["per_page"]

    logger.info("Fetching people for tree", tree_id=tree_id, page=current_page, per_page=current_per_page, sort_by=sort_by, filters=filters)
    try:
        query = db.query(Person).filter(Person.tree_id == tree_id)

        if filters:
            if 'is_living' in filters and isinstance(filters['is_living'], bool):
                query = query.filter(Person.is_living == filters['is_living'])
            if 'gender' in filters and filters['gender']: # Ensure gender filter is not empty string
                query = query.filter(Person.gender.ilike(f"%{filters['gender']}%")) # Case-insensitive partial match
            if 'name_contains' in filters and filters['name_contains']: # Ensure name_contains filter is not empty
                term = f"%{filters['name_contains']}%"
                query = query.filter(
                    or_(Person.first_name.ilike(term), 
                        Person.last_name.ilike(term),
                        Person.nickname.ilike(term), 
                        Person.maiden_name.ilike(term)) # Assuming maiden_name is EncryptedString if searched
                )
        
        # Validate sort_by attribute
        if not (sort_by and hasattr(Person, sort_by)): # Check if sort_by is None or not an attribute
            logger.warning(f"Invalid or missing sort_by column '{sort_by}' for Person. Defaulting to 'last_name'.")
            sort_by = "last_name"
        
        # Ensure sort_order is valid
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'

        return paginate_query(query, Person, current_page, current_per_page, cfg_pagination["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"fetching people for tree {tree_id}", db) # This will abort
    except HTTPException: # Re-raise aborts if they happen within this function
        raise
    except Exception as e: # Catch any other unexpected error
        logger.error("Unexpected error fetching people for tree.", tree_id=tree_id, exc_info=True)
        abort(500, description="An unexpected error occurred while fetching people.")
    return {} # Should be unreachable if aborts are working

def get_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID) -> Dict[str, Any]:
    """Fetches a single person by ID within a specific tree."""
    logger.info("Fetching person details", person_id=person_id, tree_id=tree_id)
    person = _get_or_404(db, Person, person_id, tree_id=tree_id)
    return person.to_dict()

def create_person_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new person in the database for a given tree."""
    person_name_log = f"{person_data.get('first_name', '')} {person_data.get('last_name', '')}".strip()
    logger.info("Attempting to create new person", user_id=user_id, tree_id=tree_id, person_name=person_name_log)

    if not person_data.get('first_name'):
        abort(400, description={"message": "Validation failed", "details": {"first_name": "First name is required."}})

    errors: Dict[str, str] = {} # Explicitly type errors
    birth_date_str = person_data.get('birth_date')
    death_date_str = person_data.get('death_date')
    birth_date: Optional[date] = None
    death_date: Optional[date] = None

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
         errors['gender'] = "Invalid gender value. Allowed: male, female, other, unknown, or empty to clear."
    
    privacy_level_str = person_data.get('privacy_level', PrivacyLevelEnum.inherit.value)
    try:
        privacy_level_enum = PrivacyLevelEnum(privacy_level_str)
    except ValueError:
        errors['privacy_level'] = f"Invalid privacy level: {privacy_level_str}. Valid: {[p.value for p in PrivacyLevelEnum]}"

    if errors:
        logger.warning("Person creation failed due to validation errors.", errors=errors, tree_id=tree_id)
        abort(400, description={"message": "Validation failed", "details": errors})

    try:
        new_person = Person(
            tree_id=tree_id, created_by=user_id,
            first_name=person_data['first_name'], # Already checked for presence
            middle_names=person_data.get('middle_names'),
            last_name=person_data.get('last_name'),
            maiden_name=person_data.get('maiden_name'),
            nickname=person_data.get('nickname'),
            gender=gender if gender else None, # Store None if empty string was provided
            birth_date=birth_date,
            birth_date_approx=bool(person_data.get('birth_date_approx', False)), # Ensure boolean
            birth_place=person_data.get('birth_place'),
            place_of_birth=person_data.get('place_of_birth'),
            death_date=death_date,
            death_date_approx=bool(person_data.get('death_date_approx', False)), # Ensure boolean
            death_place=person_data.get('death_place'),
            place_of_death=person_data.get('place_of_death'),
            burial_place=person_data.get('burial_place'),
            privacy_level=privacy_level_enum,
            is_living=person_data.get('is_living'), # Will be auto-set if None
            notes=person_data.get('notes'),
            biography=person_data.get('biography'),
            profile_picture_url=person_data.get('profile_picture_url'),
            custom_attributes=person_data.get('custom_attributes', {})
        )
        # If is_living is not explicitly provided, determine it based on death_date.
        if new_person.is_living is None:
            new_person.is_living = new_person.death_date is None

        db.add(new_person)
        db.commit()
        db.refresh(new_person)
        logger.info("Person created successfully", person_id=new_person.id, tree_id=tree_id, created_by=user_id)
        return new_person.to_dict()
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, "creating person", db) # This will abort
    except HTTPException: # Re-raise aborts
        raise
    except Exception as e:
        db.rollback() # Ensure rollback for non-SQLAlchemy errors
        logger.error("Unexpected error during person creation.", tree_id=tree_id, user_id=user_id, exc_info=True)
        abort(500, description="An unexpected error occurred during person creation.")
    return {} # Should be unreachable


def update_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates an existing person in the database."""
    logger.info("Attempting to update person", person_id=person_id, tree_id=tree_id, data_keys=list(person_data.keys()))
    person = _get_or_404(db, Person, person_id, tree_id=tree_id)
    
    validation_errors: Dict[str, str] = {}
    allowed_fields = [
        'first_name', 'middle_names', 'last_name', 'maiden_name', 'nickname', 'gender',
        'birth_date', 'birth_date_approx', 'birth_place', 'place_of_birth', 
        'death_date', 'death_date_approx', 'death_place', 'place_of_death', 
        'burial_place', 'privacy_level', 'is_living', 'notes', 'biography', 'profile_picture_url', 'custom_attributes'
        'profile_picture_url',  # Added profile_picture_url to allowed fields
        'custom_fields'  # Added custom_fields to allowed fields
    ]

    for field, value in person_data.items():
        if field not in allowed_fields:
            logger.warning(f"Attempt to update unallowed field '{field}' for person {person_id}.")
            continue

        try:
            if field in ['birth_date', 'death_date']:
                setattr(person, field, date.fromisoformat(value) if value is not None else None)
            elif field == 'gender':
                if value is not None and str(value).lower() not in ['male', 'female', 'other', 'unknown', '']:
                     validation_errors[field] = "Invalid gender value. Allowed: male, female, other, unknown, or empty to clear."
                else: setattr(person, field, value if value else None) # Store None if empty or None
            elif field == 'privacy_level':
                 setattr(person, field, PrivacyLevelEnum(value) if value is not None else person.privacy_level) # Keep existing if None
            elif field == 'custom_attributes':
                 if not isinstance(value, dict) and value is not None: 
                     validation_errors[field] = "Custom attributes must be a dictionary or null."
                 else: setattr(person, field, value if value is not None else {}) # Default to empty dict if null
            elif field == 'custom_fields':  # Added custom_fields handling
                 if not isinstance(value, dict) and value is not None:
                     validation_errors[field] = "Custom fields must be a dictionary or null."
                 else: setattr(person, field, value if value is not None else {}) # Default to empty dict if null
            elif field in ['is_living', 'birth_date_approx', 'death_date_approx']:
                 if not isinstance(value, bool) and value is not None: 
                     validation_errors[field] = f"{field} must be a boolean or null."
                 else: setattr(person, field, value) # Allows setting to None if desired and model allows
            else: # For other string fields
                setattr(person, field, value)
        except ValueError as e: # Catches date format errors, enum errors
            validation_errors[field] = f"Invalid value or format for {field}: {e}"
        except Exception as e: # Catch-all for unexpected issues during field processing
            logger.error(f"Unexpected error processing field {field} for person update.", exc_info=True)
            validation_errors[field] = f"Unexpected error processing {field}."

    if validation_errors:
         logger.warning("Person update failed: Validation errors.", person_id=person_id, errors=validation_errors)
         abort(400, description={"message": "Validation failed", "details": validation_errors})

    # Date consistency check
    if person.birth_date and person.death_date and person.death_date < person.birth_date:
        logger.warning("Person update failed: Death date cannot be before birth date.", person_id=person_id)
        abort(400, description={"message": "Validation failed", "details": {"date_comparison": "Death date cannot be before birth date."}})
    
    # Auto-update is_living if not explicitly set and death_date changed
    if 'is_living' not in person_data and ('death_date' in person_data or 'birth_date' in person_data): # Check if dates were part of input
         person.is_living = person.death_date is None
    
    # person.updated_at is handled by onupdate in the model
    try:
        db.commit()
        db.refresh(person)
        logger.info("Person updated successfully", person_id=person.id, tree_id=tree_id)
        return person.to_dict()
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"updating person ID {person_id}", db) # This will abort
    except HTTPException: # Re-raise aborts
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during person update.", person_id=person_id, tree_id=tree_id, exc_info=True)
        abort(500, description="An unexpected error occurred during person update.")
    return {} # Should be unreachable

def delete_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    """Deletes a person from the database."""
    logger.info("Attempting to delete person", person_id=person_id, tree_id=tree_id)
    person = _get_or_404(db, Person, person_id, tree_id=tree_id)
    person_name_for_log = f"{person.first_name or ''} {person.last_name or ''}".strip()

    try:
        db.delete(person)
        db.commit()
        logger.info("Person deleted successfully", person_id=person_id, person_name=person_name_for_log, tree_id=tree_id)
        return True
    except SQLAlchemyError as e: 
        _handle_sqlalchemy_error(e, f"deleting person ID {person_id}", db) # This will abort
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during person deletion.", person_id=person_id, tree_id=tree_id, exc_info=True)
        abort(500, description="An unexpected error occurred during person deletion.")
    return False # Should be unreachable
