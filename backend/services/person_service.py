# backend/services/person_service.py
import uuid
import structlog
from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from flask import abort

from ..models import Person, PrivacyLevelEnum
from ..utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from ..config import PAGINATION_DEFAULTS, DEFAULT_PAGE, DEFAULT_PAGE_SIZE
# from opentelemetry import trace

# tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)

def get_all_people_db(db: DBSession,
                        tree_id: uuid.UUID,
                        page: int = DEFAULT_PAGE,
                        per_page: int = DEFAULT_PAGE_SIZE,
                        sort_by: Optional[str] = "last_name",
                        sort_order: Optional[str] = "asc",
                        filters: Optional[Dict[str, Any]] = None
                        ) -> Dict[str, Any]:
    """Fetches a paginated list of people for a given tree."""
    logger.info("Fetching all people for tree", tree_id=tree_id, page=page, per_page=per_page, sort_by=sort_by, filters=filters)
    try:
        query = db.query(Person).filter(Person.tree_id == tree_id)

        if filters:
            if 'is_living' in filters and isinstance(filters['is_living'], bool):
                query = query.filter(Person.is_living == filters['is_living'])
            if 'gender' in filters and filters['gender']: # Ensure gender filter is not empty
                query = query.filter(Person.gender.ilike(f"%{filters['gender']}%")) # Case-insensitive partial match
            if 'name_contains' in filters and filters['name_contains']:
                term = f"%{filters['name_contains']}%"
                query = query.filter(
                    (Person.first_name.ilike(term)) |
                    (Person.last_name.ilike(term)) |
                    (Person.nickname.ilike(term)) |
                    (Person.maiden_name.ilike(term))
                )
        
        if not hasattr(Person, sort_by or ""): # Handle None sort_by
            logger.warning(f"Invalid sort_by column '{sort_by}' for Person. Defaulting to 'last_name'.")
            sort_by = "last_name"

        return paginate_query(query, Person, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e:
        logger.error("Database error fetching all people for tree.", tree_id=tree_id, exc_info=True)
        _handle_sqlalchemy_error(e, f"fetching all people for tree {tree_id}", db)
    except Exception as e:
        logger.error("Unexpected error fetching all people for tree.", tree_id=tree_id, exc_info=True)
        abort(500, "An unexpected error occurred while fetching people.")
    return {} # Should be unreachable

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

    errors = {}
    birth_date_str = person_data.get('birth_date')
    death_date_str = person_data.get('death_date')
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
            first_name=person_data['first_name'],
            middle_names=person_data.get('middle_names'),
            last_name=person_data.get('last_name'),
            maiden_name=person_data.get('maiden_name'),
            nickname=person_data.get('nickname'),
            gender=gender if gender else None,
            birth_date=birth_date,
            birth_date_approx=person_data.get('birth_date_approx', False),
            birth_place=person_data.get('birth_place'),
            death_date=death_date,
            death_date_approx=person_data.get('death_date_approx', False),
            death_place=person_data.get('death_place'),
            burial_place=person_data.get('burial_place'),
            privacy_level=privacy_level_enum,
            is_living=person_data.get('is_living'),
            notes=person_data.get('notes'),
            custom_attributes=person_data.get('custom_attributes', {})
        )
        if new_person.is_living is None:
            new_person.is_living = new_person.death_date is None

        db.add(new_person)
        db.commit()
        db.refresh(new_person)
        logger.info("Person created successfully", person_id=new_person.id, tree_id=tree_id, created_by=user_id)
        return new_person.to_dict()
    except SQLAlchemyError as e:
        logger.error("Database error during person creation.", tree_id=tree_id, exc_info=True)
        _handle_sqlalchemy_error(e, "creating person", db)
    except Exception as e:
        db.rollback() # Ensure rollback for non-SQLAlchemy errors
        logger.error("Unexpected error during person creation.", tree_id=tree_id, exc_info=True)
        abort(500, description="An unexpected error occurred during person creation.")
    return {} # Should be unreachable


def update_person_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID, person_data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates an existing person in the database."""
    logger.info("Attempting to update person", person_id=person_id, tree_id=tree_id, data_keys=list(person_data.keys()))
    person = _get_or_404(db, Person, person_id, tree_id=tree_id)
    
    validation_errors = {}
    allowed_fields = [
        'first_name', 'middle_names', 'last_name', 'maiden_name', 'nickname', 'gender',
        'birth_date', 'birth_date_approx', 'birth_place', 'death_date', 'death_date_approx',
        'death_place', 'burial_place', 'privacy_level', 'is_living', 'notes', 'custom_attributes'
    ]

    for field, value in person_data.items():
        if field not in allowed_fields:
            logger.warning(f"Attempt to update unallowed field '{field}' for person {person_id}.")
            continue

        try:
            if field in ['birth_date', 'death_date']:
                setattr(person, field, date.fromisoformat(value) if value else None)
            elif field == 'gender':
                if value is not None and str(value).lower() not in ['male', 'female', 'other', 'unknown', '']:
                     validation_errors[field] = "Invalid gender value."
                else: setattr(person, field, value if value else None)
            elif field == 'privacy_level':
                 setattr(person, field, PrivacyLevelEnum(value) if value else person.privacy_level) # Keep existing if None
            elif field == 'custom_attributes':
                 if not isinstance(value, dict): validation_errors[field] = "Custom attributes must be a dictionary."
                 else: setattr(person, field, value)
            elif field in ['is_living', 'birth_date_approx', 'death_date_approx']:
                 if not isinstance(value, bool): validation_errors[field] = f"{field} must be a boolean."
                 else: setattr(person, field, value)
            else: # String fields
                setattr(person, field, value)
        except ValueError as e:
            validation_errors[field] = f"Invalid value or format for {field}: {e}"
        except Exception as e:
            logger.error(f"Unexpected error processing field {field} for person update.", exc_info=True)
            validation_errors[field] = f"Unexpected error processing {field}."

    if validation_errors:
         logger.warning("Person update failed: Validation errors.", person_id=person_id, errors=validation_errors)
         abort(400, description={"message": "Validation failed", "details": validation_errors})

    if person.birth_date and person.death_date and person.death_date < person.birth_date:
        abort(400, description={"message": "Validation failed", "details": {"date_comparison": "Death date cannot be before birth date."}})
    
    if 'is_living' not in person_data and ('death_date' in person_data or 'birth_date' in person_data):
         person.is_living = person.death_date is None
    
    try:
        db.commit()
        db.refresh(person)
        logger.info("Person updated successfully", person_id=person.id, tree_id=tree_id)
        return person.to_dict()
    except SQLAlchemyError as e:
        logger.error("Database error during person update.", person_id=person_id, exc_info=True)
        _handle_sqlalchemy_error(e, f"updating person ID {person_id}", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during person update.", person_id=person_id, exc_info=True)
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
    except SQLAlchemyError as e: # Catches IntegrityError if person is part of relationships
        logger.error("Database error during person deletion.", person_id=person_id, exc_info=True)
        # _handle_sqlalchemy_error will check for foreign key violations.
        _handle_sqlalchemy_error(e, f"deleting person ID {person_id}", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during person deletion.", person_id=person_id, exc_info=True)
        abort(500, description="An unexpected error occurred during person deletion.")
    return False # Should be unreachable
