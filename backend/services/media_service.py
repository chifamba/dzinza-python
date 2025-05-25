# backend/services/media_service.py
import uuid
import structlog
import os
from typing import Dict, Any, Optional, IO
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from flask import abort
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename


# Absolute imports from the app root
from models import MediaItem, MediaTypeEnum, Person, Tree, Event, Relationship # Event (if/when Event model exists)
from utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from config import config # Direct import of the config instance
from storage_client import get_storage_client, create_bucket_if_not_exists

logger = structlog.get_logger(__name__)

# Helper to map content_type to MediaTypeEnum
def _infer_file_type(content_type: Optional[str], filename: Optional[str]) -> MediaTypeEnum:
    if content_type:
        if content_type.startswith('image/'): return MediaTypeEnum.photo
        elif content_type.startswith('audio/'): return MediaTypeEnum.audio
        elif content_type.startswith('video/'): return MediaTypeEnum.video
        elif content_type == 'application/pdf': return MediaTypeEnum.document
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']: return MediaTypeEnum.photo
        elif ext in ['.mp3', '.wav', '.ogg']: return MediaTypeEnum.audio
        elif ext in ['.mp4', '.mov', '.avi']: return MediaTypeEnum.video
        elif ext == '.pdf': return MediaTypeEnum.document
    return MediaTypeEnum.other

def get_media_item_db(db: DBSession, media_id: uuid.UUID) -> Dict[str, Any]:
    # Removed tree_id from parameters
    """Fetches a single media item by its ID."""
    logger.info("Fetching media item", media_id=media_id)
    # Fetch globally. Authorization (e.g. if user can access this media) is a higher-level concern.
    media_item = _get_or_404(db, MediaItem, media_id)
    return media_item.to_dict()

def upload_media_item_db(db: DBSession, user_id: uuid.UUID, 
                         tree_id_context: Optional[uuid.UUID], # The tree user is currently in, can be None
                         linked_entity_type: str, 
                         linked_entity_id: uuid.UUID, 
                         file_stream: IO[bytes], filename: str, content_type: str, 
                         caption: Optional[str] = None, 
                         file_type_enum_provided: Optional[MediaTypeEnum] = None) -> Dict[str, Any]:
    """
    Uploads a media file to S3, creates a MediaItem record in the database,
    and links it to a specified entity.
    MediaItem.tree_id is set to None for Person-linked media (global to person),
    and to the tree's ID for Tree-linked media.
    """
    logger.info("Attempting to upload media item", user_id=user_id, tree_id_context=tree_id_context,
                linked_entity_type=linked_entity_type, linked_entity_id=linked_entity_id, filename=filename)

    media_item_tree_id: Optional[uuid.UUID] = None # Default to None (for global entities like Person)

    # Validate linked entity and determine MediaItem.tree_id
    if linked_entity_type == "Person":
        _get_or_404(db, Person, linked_entity_id) # Check person exists globally
        media_item_tree_id = None # Media linked to a Person is global (tree_id is NULL)
    elif linked_entity_type == "Tree":
        tree_entity = _get_or_404(db, Tree, linked_entity_id)
        media_item_tree_id = tree_entity.id # Media linked to a Tree has tree_id set
        # If tree_id_context is provided, it should match for tree-specific media.
        if tree_id_context and tree_id_context != media_item_tree_id:
            logger.warning("tree_id_context mismatch when linking media directly to a Tree entity.",
                           provided_tree_id_context=tree_id_context, target_tree_id=media_item_tree_id)
            abort(400, "Context tree ID mismatch for Tree entity media.")
    elif linked_entity_type == "Event": # Assuming Event is global
        _get_or_404(db, Event, linked_entity_id)
        media_item_tree_id = None
    elif linked_entity_type == "Relationship": # Assuming Relationship is global
        _get_or_404(db, Relationship, linked_entity_id)
        media_item_tree_id = None
    else:
        logger.warning("Unsupported entity type for media linking.", entity_type=linked_entity_type)
        abort(400, description=f"Unsupported entity type: {linked_entity_type}")
    
    # Authorization: This is simplified. Real authorization would check if user_id
    # has rights to attach media to the specific linked_entity_id, possibly using tree_id_context.
    # For now, we just check entity existence.

    try:
        s3_client = get_storage_client()
        if not s3_client:
            logger.error("S3 client not available for media upload.")
            abort(500, description="Storage service is currently unavailable.")

        if not create_bucket_if_not_exists(s3_client, config.OBJECT_STORAGE_BUCKET_NAME):
            logger.error("Bucket could not be verified/created for media upload.", bucket_name=config.OBJECT_STORAGE_BUCKET_NAME)
            abort(500, description="Storage bucket is not ready.")

        final_file_type = file_type_enum_provided if file_type_enum_provided else _infer_file_type(content_type, filename)
        
        secured_filename = secure_filename(filename)
        file_extension = os.path.splitext(secured_filename)[1]
        
        # Object key path changes based on whether it's tree-specific or global
        if media_item_tree_id: # Tree-specific media (e.g., linked to Tree entity)
            object_key_prefix = f"media/tree/{media_item_tree_id}"
        elif linked_entity_type == "Person": # Person-specific global media
             object_key_prefix = f"media/person/{linked_entity_id}"
        else: # Other global entities
            object_key_prefix = f"media/global/{linked_entity_type.lower()}/{linked_entity_id}"
            
        object_key = f"{object_key_prefix}/{uuid.uuid4()}{file_extension}"


        # Get file size
        file_stream.seek(0, os.SEEK_END)
        file_size = file_stream.tell()
        file_stream.seek(0) # Reset stream position for upload

        if file_size == 0:
            abort(400, description="Cannot upload empty file.")

        logger.debug(f"Uploading media to S3: bucket='{config.OBJECT_STORAGE_BUCKET_NAME}', key='{object_key}'")
        s3_client.upload_fileobj(file_stream, config.OBJECT_STORAGE_BUCKET_NAME, object_key, ExtraArgs={'ContentType': content_type})

        new_media_item = MediaItem(
            uploader_user_id=user_id,
            tree_id=media_item_tree_id, # This is now correctly None for Person, or TreeID for Tree
            file_name=secured_filename,
            file_type=final_file_type,
            mime_type=content_type,
            file_size=file_size,
            storage_path=object_key,
            linked_entity_type=linked_entity_type,
            linked_entity_id=linked_entity_id,
            caption=caption,
            thumbnail_url=None # Placeholder for future thumbnail generation
        )

        db.add(new_media_item)
        db.commit()
        db.refresh(new_media_item)
        
        logger.info("Media item uploaded and record created successfully.", media_item_id=new_media_item.id, object_key=object_key)
        return new_media_item.to_dict()

    except (S3UploadFailedError, ClientError) as e:
        db.rollback()
        logger.error("S3 operation failed for media upload.", error=str(e), exc_info=True)
        abort(500, description="Failed to upload media file to storage.")
    except SQLAlchemyError as e:
        db.rollback()
        _handle_sqlalchemy_error(e, "creating media item DB record", db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during media upload.", error=str(e), exc_info=True)
        abort(500, description="An unexpected error occurred while processing the media file.")
    return {}


def delete_media_item_db(db: DBSession, media_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    # Removed tree_id from parameters
    """
    Deletes a media item from S3 and its record from the database.
    Authorization: User must be uploader. More complex auth (e.g. tree admin) is a higher-level concern.
    """
    logger.info("Attempting to delete media item", media_id=media_id, user_id=user_id)
    
    media_item = _get_or_404(db, MediaItem, media_id) # Fetch globally

    # Authorization check: For now, only uploader can delete.
    # If tree_id context were passed, could add checks for tree admin rights if media_item.tree_id is set.
    if media_item.uploader_user_id != user_id:
        logger.warning("User not authorized to delete media item.", media_item_id=media_id, 
                       requesting_user_id=user_id, uploader_user_id=media_item.uploader_user_id)
        abort(403, description="You are not authorized to delete this media item.")

    try:
        s3_client = get_storage_client()
        if not s3_client:
            logger.error("S3 client not available for media deletion.")
            # Potentially allow DB record deletion even if S3 client fails, or make it stricter
            abort(500, description="Storage service is currently unavailable, cannot delete file.")

        logger.info(f"Deleting media object from S3: bucket='{config.OBJECT_STORAGE_BUCKET_NAME}', key='{media_item.storage_path}'")
        try:
            s3_client.delete_object(Bucket=config.OBJECT_STORAGE_BUCKET_NAME, Key=media_item.storage_path)
            logger.info("S3 object deleted successfully or was already absent.", s3_key=media_item.storage_path)
        except ClientError as e:
            # Log S3 deletion error but proceed to delete DB record to avoid orphaned S3 objects being inaccessible
            logger.error(f"Failed to delete object {media_item.storage_path} from S3. Proceeding with DB record deletion.",
                         error=str(e), exc_info=True)
            # Depending on policy, you might choose to abort here if S3 deletion is critical and must succeed.

        db.delete(media_item)
        db.commit()
        
        logger.info("Media item record deleted successfully from DB.", media_item_id=media_id)
        return True

    except (S3UploadFailedError, ClientError) as e: # Should be caught by specific delete_object try-except
        db.rollback() # Rollback DB changes if any step after S3 interaction fails before commit
        logger.error("S3 operation error during media deletion process.", media_item_id=media_id, error=str(e), exc_info=True)
        abort(500, description="A storage service error occurred during media deletion.")
    except SQLAlchemyError as e:
        db.rollback()
        _handle_sqlalchemy_error(e, "deleting media item DB record", db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during media deletion.", media_item_id=media_id, error=str(e), exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the media item.")
    return False


def get_media_for_entity_db(db: DBSession, entity_type: str, entity_id: uuid.UUID, 
                              page: int = -1, per_page: int = -1, # -1 means use config default
                              sort_by: Optional[str] = "created_at",
                              sort_order: Optional[str] = "desc",
                              tree_id_context: Optional[uuid.UUID] = None # Used for Tree entity type to ensure correct tree
                             ) -> Dict[str, Any]:
    """Fetches paginated media items linked to a specific entity."""
    current_page = page if page != -1 else config.PAGINATION_DEFAULTS["page"]
    current_per_page = per_page if per_page != -1 else config.PAGINATION_DEFAULTS["per_page"]

    logger.info("Fetching media for entity", entity_type=entity_type, entity_id=entity_id, 
                tree_id_context=tree_id_context, page=current_page, per_page=current_per_page)
    try:
        query = db.query(MediaItem).filter(
            MediaItem.linked_entity_type == entity_type,
            MediaItem.linked_entity_id == entity_id
        )

        # Adjust query based on entity_type for tree_id handling
        if entity_type == "Tree":
            # For Tree entities, media_item.tree_id must match the entity_id (which is the tree's ID)
            # Also, tree_id_context (if provided) should match this entity_id for consistency.
            if tree_id_context and tree_id_context != entity_id:
                 logger.warning("tree_id_context mismatch when fetching media for a Tree entity.", 
                                tree_id_context=tree_id_context, entity_id=entity_id)
                 abort(400, "Tree context ID does not match the requested Tree entity ID for media.")
            query = query.filter(MediaItem.tree_id == entity_id)
        elif entity_type in ["Person", "Event", "Relationship"]: # Global entities
            query = query.filter(MediaItem.tree_id.is_(None))
        else:
            logger.warning(f"Fetching media for unsupported entity type: {entity_type}. This might yield unexpected results if tree_id logic is not defined.")
            # For unknown types, we might default to assuming tree_id should be NULL, or add specific handling.
            # For now, no additional tree_id filter beyond what's set by linked_entity_type logic during upload.
            # This means if an unsupported type *could* have a tree_id, it would be fetched.
            # However, upload logic currently sets tree_id=None for Event/Relationship.

        if not (sort_by and hasattr(MediaItem, sort_by)):
            logger.warning(f"Invalid or missing sort_by column '{sort_by}' for MediaItem. Defaulting to 'created_at'.")
            sort_by = "created_at"
        
        if sort_order not in ['asc', 'desc']:
            logger.warning(f"Invalid sort_order '{sort_order}'. Defaulting to 'desc'.")
            sort_order = 'desc'

        return paginate_query(query, MediaItem, current_page, current_per_page, config.PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"fetching media for entity {entity_type}:{entity_id}", db)
    except HTTPException: # Re-raise aborts
        raise
    except Exception as e: # Catch any other unexpected error
        logger.error("Unexpected error fetching media for entity.", exc_info=True, tree_id=tree_id, entity_type=entity_type, entity_id=entity_id)
        abort(500, description="An unexpected error occurred while fetching media for the entity.")
    return {} # Should be unreachable
