# backend/services/event_service.py
import uuid
import structlog
from datetime import date
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_ # For querying related_person_ids
from flask import abort
from werkzeug.exceptions import HTTPException

from models import Event, Person, PrivacyLevelEnum # Assuming Event model is updated
from utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from config import config # For pagination defaults

logger = structlog.get_logger(__name__)

def _validate_person_ids(db: DBSession, tree_id: uuid.UUID, person_ids: List[str], field_name: str) -> List[uuid.UUID]:
    """Helper to validate a list of person ID strings and ensure they belong to the tree."""
    if not isinstance(person_ids, list):
        abort(400, description={"message": "Validation failed", "details": {field_name: "Must be a list of person IDs."}})
    
    valid_uuids: List[uuid.UUID] = []
    errors: List[str] = []
    for pid_str in person_ids:
        try:
            person_uuid = uuid.UUID(pid_str)
            # Check if person exists and belongs to the tree
            person = db.query(Person.id).filter(Person.id == person_uuid, Person.tree_id == tree_id).one_or_none()
            if not person:
                errors.append(f"Person with ID {pid_str} not found in tree {tree_id}.")
            else:
                valid_uuids.append(person_uuid)
        except ValueError:
            errors.append(f"Invalid UUID format for person ID: {pid_str}.")
    
    if errors:
        abort(400, description={"message": "Validation failed", "details": {field_name: errors}})
    return valid_uuids


def create_event_db(db: DBSession, user_id: uuid.UUID, tree_id: uuid.UUID, event_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Creating event", user_id=user_id, tree_id=tree_id, data_keys=list(event_data.keys()))
    
    errors: Dict[str, Any] = {}
    if not event_data.get('event_type'):
        errors['event_type'] = "Event type is required."

    # Validate person_id if provided
    person_id_str = event_data.get('person_id')
    person_id: Optional[uuid.UUID] = None
    if person_id_str:
        try:
            person_id = uuid.UUID(person_id_str)
            _get_or_404(db, Person, person_id, tree_id=tree_id) # Validates existence in tree
        except ValueError:
            errors['person_id'] = f"Invalid UUID format: {person_id_str}"
        except HTTPException as e: # Catch 404 from _get_or_404
             errors['person_id'] = str(e.description)


    # Validate related_person_ids if provided
    related_person_ids_str_list = event_data.get('related_person_ids', [])
    validated_related_person_ids: List[uuid.UUID] = []
    if related_person_ids_str_list: # Only validate if list is not empty
        try:
            # This helper will abort on failure, so we catch it to aggregate errors
            validated_related_person_ids = _validate_person_ids(db, tree_id, related_person_ids_str_list, "related_person_ids")
        except HTTPException as e: # Catch abort from _validate_person_ids
            errors['related_person_ids'] = e.description.get("details", {}).get("related_person_ids", "Validation failed.")


    # Validate date fields
    event_date_str = event_data.get('date')
    event_date: Optional[date] = None
    if event_date_str:
        try: event_date = date.fromisoformat(event_date_str)
        except ValueError: errors['date'] = "Invalid date format (YYYY-MM-DD)."

    date_range_start_str = event_data.get('date_range_start')
    date_range_start: Optional[date] = None
    if date_range_start_str:
        try: date_range_start = date.fromisoformat(date_range_start_str)
        except ValueError: errors['date_range_start'] = "Invalid date format (YYYY-MM-DD)."
    
    date_range_end_str = event_data.get('date_range_end')
    date_range_end: Optional[date] = None
    if date_range_end_str:
        try: date_range_end = date.fromisoformat(date_range_end_str)
        except ValueError: errors['date_range_end'] = "Invalid date format (YYYY-MM-DD)."

    if date_range_start and date_range_end and date_range_end < date_range_start:
        errors.setdefault('date_comparison', []).append("date_range_end cannot be before date_range_start.")

    # Validate privacy_level
    privacy_level_str = event_data.get('privacy_level', PrivacyLevelEnum.inherit.value)
    try:
        privacy_level_enum = PrivacyLevelEnum(privacy_level_str)
    except ValueError:
        errors['privacy_level'] = f"Invalid privacy level: {privacy_level_str}. Valid: {[p.value for p in PrivacyLevelEnum]}"

    if errors:
        logger.warning("Event creation failed due to validation errors.", errors=errors, tree_id=tree_id)
        abort(400, description={"message": "Validation failed", "details": errors})

    try:
        new_event = Event(
            tree_id=tree_id,
            created_by=user_id,
            person_id=person_id, # Validated UUID or None
            event_type=event_data['event_type'],
            date=event_date,
            date_approx=event_data.get('date_approx', False),
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            place=event_data.get('place'),
            description=event_data.get('description'),
            custom_attributes=event_data.get('custom_attributes', {}),
            related_person_ids=[str(pid) for pid in validated_related_person_ids], # Store as list of strings
            privacy_level=privacy_level_enum
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        logger.info("Event created successfully", event_id=new_event.id, tree_id=tree_id)
        return new_event.to_dict()
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, "creating event", db)
    except Exception as e: # Catch any other unexpected error
        db.rollback()
        logger.error("Unexpected error during event creation.", exc_info=True, details=str(e))
        abort(500, description="An unexpected error occurred during event creation.")
    return {}


def get_event_db(db: DBSession, event_id: uuid.UUID, tree_id: uuid.UUID) -> Dict[str, Any]:
    logger.info("Fetching event", event_id=event_id, tree_id=tree_id)
    event = _get_or_404(db, Event, event_id, tree_id=tree_id)
    return event.to_dict()


def update_event_db(db: DBSession, event_id: uuid.UUID, tree_id: uuid.UUID, event_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Updating event", event_id=event_id, tree_id=tree_id, data_keys=list(event_data.keys()))
    event = _get_or_404(db, Event, event_id, tree_id=tree_id) # Ensure event belongs to tree
    
    validation_errors: Dict[str, Any] = {}
    allowed_fields = [
        'person_id', 'event_type', 'date', 'date_approx', 'date_range_start', 
        'date_range_end', 'place', 'description', 'custom_attributes', 
        'related_person_ids', 'privacy_level'
    ]

    for field, value in event_data.items():
        if field not in allowed_fields:
            logger.warning(f"Attempt to update unallowed field '{field}' for event {event_id}.")
            continue
        
        try:
            if field == 'person_id':
                if value is None: # Allowing to clear person_id
                    setattr(event, field, None)
                else:
                    pid = uuid.UUID(str(value))
                    _get_or_404(db, Person, pid, tree_id=tree_id) # Validate person exists in tree
                    setattr(event, field, pid)
            elif field == 'related_person_ids':
                if value is None: # Allowing to clear related_person_ids
                    setattr(event, field, [])
                else:
                    # This helper will abort on failure, so we catch it to aggregate errors
                    # We need to handle the HTTPException if _validate_person_ids aborts
                    try:
                        validated_ids = _validate_person_ids(db, tree_id, value, "related_person_ids")
                        setattr(event, field, [str(pid) for pid in validated_ids])
                    except HTTPException as e_val:
                         validation_errors[field] = e_val.description.get("details", {}).get("related_person_ids", "Invalid person IDs.")
            elif field in ['date', 'date_range_start', 'date_range_end']:
                setattr(event, field, date.fromisoformat(str(value)) if value else None)
            elif field == 'privacy_level':
                setattr(event, field, PrivacyLevelEnum(value) if value else event.privacy_level)
            elif field == 'custom_attributes':
                if not isinstance(value, dict) and value is not None:
                    validation_errors[field] = "Custom attributes must be a dictionary or null."
                else:
                    setattr(event, field, value if value is not None else {})
            else: # For event_type, date_approx, place, description
                setattr(event, field, value)
        except ValueError as e:
            validation_errors[field] = f"Invalid value or format for {field}: {e}"
        except HTTPException as e_http: # Catch 404 from _get_or_404 for person_id
            validation_errors[field] = str(e_http.description)


    if event.date_range_start and event.date_range_end and event.date_range_end < event.date_range_start:
         validation_errors.setdefault('date_comparison', []).append("date_range_end cannot be before date_range_start.")

    if validation_errors:
        logger.warning("Event update failed due to validation errors.", errors=validation_errors, event_id=event_id)
        abort(400, description={"message": "Validation failed", "details": validation_errors})

    try:
        db.commit()
        db.refresh(event)
        logger.info("Event updated successfully", event_id=event.id)
        return event.to_dict()
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"updating event ID {event_id}", db)
    except Exception as e: # Catch any other unexpected error
        db.rollback()
        logger.error("Unexpected error during event update.", exc_info=True, event_id=event_id)
        abort(500, description="An unexpected error occurred during event update.")
    return {}


def delete_event_db(db: DBSession, event_id: uuid.UUID, tree_id: uuid.UUID) -> bool:
    logger.info("Deleting event", event_id=event_id, tree_id=tree_id)
    event = _get_or_404(db, Event, event_id, tree_id=tree_id)
    try:
        db.delete(event)
        db.commit()
        logger.info("Event deleted successfully", event_id=event_id)
        return True
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"deleting event ID {event_id}", db)
    except Exception as e: # Catch any other unexpected error
        db.rollback()
        logger.error("Unexpected error during event deletion.", exc_info=True, event_id=event_id)
        abort(500, description="An unexpected error occurred during event deletion.")
    return False


def get_events_for_person_db(db: DBSession, tree_id: uuid.UUID, person_id: uuid.UUID, 
                               page: int, per_page: int, 
                               sort_by: Optional[str], sort_order: Optional[str]) -> Dict[str, Any]:
    logger.info("Fetching events for person", tree_id=tree_id, person_id=person_id, page=page, per_page=per_page)
    # Ensure person exists in the tree
    _get_or_404(db, Person, person_id, tree_id=tree_id)
    
    try:
        # Query for events where person_id matches OR person_id is in related_person_ids
        # Note: JSONB array operations can be tricky with SQLAlchemy across DBs.
        # For PostgreSQL, `array_to_string` and `LIKE` or `@>` operator can be used.
        # Using stringified UUIDs in the JSONB array for simpler querying.
        person_id_str = str(person_id)
        query = db.query(Event).filter(
            Event.tree_id == tree_id,
            or_(
                Event.person_id == person_id,
                Event.related_person_ids.cast(sa.Text).like(f'%"{person_id_str}"%') # Assumes UUIDs are stored as strings in JSON list
            )
        )
        
        sort_by_attr = sort_by if (sort_by and hasattr(Event, sort_by)) else "date" # Default sort by date
        if sort_by_attr == "date" and not hasattr(Event, "date"): sort_by_attr="created_at" # Fallback if date isn't on model (it is)

        return paginate_query(query, Event, page, per_page, config.PAGINATION_DEFAULTS["max_per_page"], sort_by_attr, sort_order or "asc")
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"fetching events for person {person_id}", db)
    except Exception as e: # Catch any other unexpected error
        logger.error("Unexpected error fetching events for person.", exc_info=True, person_id=person_id)
        abort(500, description="An unexpected error occurred while fetching events for the person.")
    return {}


def get_events_for_tree_db(db: DBSession, tree_id: uuid.UUID, 
                             page: int, per_page: int, 
                             sort_by: Optional[str], sort_order: Optional[str], 
                             filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    logger.info("Fetching events for tree", tree_id=tree_id, page=page, per_page=per_page, filters=filters)
    try:
        query = db.query(Event).filter(Event.tree_id == tree_id)
        
        if filters:
            if 'event_type' in filters and filters['event_type']:
                query = query.filter(Event.event_type.ilike(f"%{filters['event_type']}%"))
            # Add more filters as needed, e.g., date range

        sort_by_attr = sort_by if (sort_by and hasattr(Event, sort_by)) else "date"
        if sort_by_attr == "date" and not hasattr(Event, "date"): sort_by_attr="created_at"

        return paginate_query(query, Event, page, per_page, config.PAGINATION_DEFAULTS["max_per_page"], sort_by_attr, sort_order or "asc")
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"fetching events for tree {tree_id}", db)
    except Exception as e: # Catch any other unexpected error
        logger.error("Unexpected error fetching events for tree.", exc_info=True, tree_id=tree_id)
        abort(500, description="An unexpected error occurred while fetching events for the tree.")
    return {}
