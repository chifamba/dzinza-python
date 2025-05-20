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

import os # For path manipulation if needed for filename
from werkzeug.utils import secure_filename # For sanitizing filenames
from botocore.exceptions import S3UploadFailedError, ClientError # More specific Boto3 exceptions

# Absolute imports from the app root
from models import Person, PrivacyLevelEnum # MediaItem, MediaTypeEnum (Not needed for this task)
from utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from config import config # Direct import of the config instance
from storage_client import get_storage_client, create_bucket_if_not_exists
# from services.media_service import create_media_item_record_db # Not using for direct profile pic update

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
            custom_attributes=person_data.get('custom_attributes', {}),
            profile_picture_url=person_data.get('profile_picture_url'),  # Added profile_picture_url
            custom_fields=person_data.get('custom_fields', {})  # Added custom_fields
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
        'burial_place', 'privacy_level', 'is_living', 'notes', 'biography', 'custom_attributes',
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


def upload_profile_picture_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID, 
                              user_id: uuid.UUID, # user_id for auditing, consistency
                              file_stream, filename: str, content_type: str) -> Dict[str, Any]:
    """
    Uploads a profile picture for a person, saves it to object storage,
    and updates the person's profile_picture_url with the object key.
    """
    logger.info("Attempting to upload profile picture", person_id=person_id, tree_id=tree_id, filename=filename)
    
    person = _get_or_404(db, Person, person_id, tree_id=tree_id)

    try:
        s3_client = get_storage_client()
        if not s3_client:
             logger.error("S3 client not available for profile picture upload.", person_id=person_id)
             abort(500, description="Storage service is currently unavailable.")

        # Ensure bucket exists (optional here if app startup guarantees it, but good for robustness)
        if not create_bucket_if_not_exists(s3_client, config.OBJECT_STORAGE_BUCKET_NAME):
            logger.error("Bucket could not be verified or created for profile picture upload.", bucket_name=config.OBJECT_STORAGE_BUCKET_NAME)
            abort(500, description="Storage bucket is not ready.")

        # Sanitize filename before using it in the path
        secured_filename = secure_filename(filename)
        # Generate a unique object key
        # Example: "profile_pictures/tree_uuid/person_uuid/random_uuid_original_filename.ext"
        file_extension = os.path.splitext(secured_filename)[1]
        object_key = f"profile_pictures/{tree_id}/{person_id}/{uuid.uuid4()}{file_extension}"
        
        logger.debug(f"Uploading to S3: bucket='{config.OBJECT_STORAGE_BUCKET_NAME}', key='{object_key}'")

        s3_client.upload_fileobj(
            file_stream,
            config.OBJECT_STORAGE_BUCKET_NAME,
            object_key,
            ExtraArgs={'ContentType': content_type}
        )
        
        # Store the object key as the profile_picture_url
        # The full URL can be constructed on the client-side or via a dedicated endpoint if needed
        # This also handles potential deletion: if a new picture is uploaded, the old key is overwritten.
        # For actual deletion of old S3 objects, a separate mechanism would be needed if person.profile_picture_url stores the old key.
        
        old_object_key = person.profile_picture_url
        if old_object_key and old_object_key != object_key:
            try:
                logger.info(f"Deleting old profile picture from S3: {old_object_key}", person_id=person_id)
                s3_client.delete_object(Bucket=config.OBJECT_STORAGE_BUCKET_NAME, Key=old_object_key)
            except ClientError as e:
                logger.error(f"Failed to delete old profile picture {old_object_key} from S3.", error=str(e), person_id=person_id)
                # Non-critical error, so we don't abort the upload of the new picture

        person.profile_picture_url = object_key
        db.commit()
        db.refresh(person)
        
        logger.info("Profile picture uploaded and person record updated successfully.",
                    person_id=person_id, object_key=object_key)
        return person.to_dict()

    except S3UploadFailedError as e:
        db.rollback()
        logger.error("S3 upload failed for profile picture.", person_id=person_id, error=str(e), exc_info=True)
        abort(500, description="Failed to upload profile picture to storage.")
    except ClientError as e: # Catch other Boto3 client errors
        db.rollback()
        logger.error("Boto3 client error during profile picture upload.", person_id=person_id, error=str(e), exc_info=True)
        abort(500, description="A storage service error occurred.")
    except SQLAlchemyError as e:
        db.rollback() # Rollback SQLAlchemy transaction
        _handle_sqlalchemy_error(e, f"updating person profile_picture_url for person ID {person_id}", db) # This will abort
    except HTTPException: # Re-raise aborts
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during profile picture upload.", person_id=person_id, error=str(e), exc_info=True)
        abort(500, description="An unexpected error occurred while processing the profile picture.")
    return {} # Should be unreachable
