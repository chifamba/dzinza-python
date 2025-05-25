# backend/services/tree_service.py
import uuid
import structlog
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_
import os
from flask import abort
from werkzeug.utils import secure_filename
from flask import abort # Ensure abort is imported if used in user fetching
# from botocore.exceptions import S3UploadFailedError, ClientError


from models import Tree, TreeAccess, Person, Relationship, PrivacyLevelEnum, TreePrivacySettingEnum, User, UserRole # Added User, UserRole
from utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from config import config # Direct import of the config instance
# import config as app_config_module # Keep this if used by get_user_trees_db's cfg_pagination
from storage_client import get_storage_client, create_bucket_if_not_exists


logger = structlog.get_logger(__name__)

def create_tree_db(db: DBSession, user_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    tree_name = tree_data.get('name')
    logger.info("Creating new tree", user_id=user_id, tree_name=tree_name)
    if not tree_name: abort(400, description="Tree name is required.") # Use description consistently
    
    try: 
        default_privacy_enum = PrivacyLevelEnum(tree_data.get('default_privacy_level', PrivacyLevelEnum.private.value))
    except ValueError: 
        abort(400, description=f"Invalid default_privacy_level: {tree_data.get('default_privacy_level')}.")

    privacy_setting_str = tree_data.get('privacy_setting', TreePrivacySettingEnum.PRIVATE.value)
    try:
        privacy_setting_enum = TreePrivacySettingEnum(privacy_setting_str)
    except ValueError:
        abort(400, description=f"Invalid privacy_setting: {privacy_setting_str}.")

    try:
        new_tree = Tree(
            name=tree_name, 
            description=tree_data.get('description'), 
            created_by=user_id,
            default_privacy_level=default_privacy_enum,
            privacy_setting=privacy_setting_enum # Set new field
            # is_public field is removed from direct assignment
        )
        db.add(new_tree); db.flush() # Flush to get new_tree.id for TreeAccess
        tree_access = TreeAccess(tree_id=new_tree.id, user_id=user_id, access_level='admin', granted_by=user_id)
        db.add(tree_access); db.commit(); db.refresh(new_tree) # Commit all changes
        logger.info("Tree created with owner access.", tree_id=new_tree.id, created_by=user_id)
        return new_tree.to_dict()
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "creating tree", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error creating tree.", user_id=user_id, exc_info=True)
        abort(500, "Error creating tree.")
    return {}

def get_user_trees_db(db: DBSession, user_id: uuid.UUID, page: int = -1, per_page: int = -1,
                        sort_by: Optional[str] = "name", sort_order: Optional[str] = "asc"
                        ) -> Dict[str, Any]:
    # cfg_pagination = app_config_module.config.PAGINATION_DEFAULTS # Using direct config import
    current_page = page if page != -1 else config.PAGINATION_DEFAULTS["page"]
    current_per_page = per_page if per_page != -1 else config.PAGINATION_DEFAULTS["per_page"]
    logger.info("Fetching trees for user", user_id=user_id, page=current_page, per_page=current_per_page)

    try:
        user = db.query(User).filter(User.id == user_id).one_or_none()
        if not user:
            # This case should ideally not be reached if user_id is from a validated session.
            # If it can happen, aborting might be safer. For now, log and proceed (will likely return empty).
            logger.error("User not found when trying to fetch trees. Service layer error.", user_id=user_id)
            # Consider abort(404, "User not found") if this indicates a severe issue.
            # For now, let it result in an empty list for non-admins or all trees for a non-existent admin (which is unlikely).
            # This path implies an issue upstream or data integrity problem.
            # Depending on strictness, could raise an exception or abort.
            # For this exercise, if user is None, the 'else' block for non-admin will be hit.
            # If UserRole.admin comparison is done, it would be `None.role` -> AttributeError.
            # So, explicit check for user is important.

        if user and user.role == UserRole.admin:
            logger.info("Admin user detected. Fetching all trees.", admin_user_id=user_id)
            query = db.query(Tree)
        else:
            logger.info("Non-admin user or user not found. Fetching owned and shared trees.", user_id=user_id)
            owned_trees_sq = db.query(Tree.id.label("tree_id")).filter(Tree.created_by == user_id)
            shared_trees_sq = db.query(TreeAccess.tree_id.label("tree_id")).filter(TreeAccess.user_id == user_id)
            accessible_tree_ids_sq = owned_trees_sq.union(shared_trees_sq).distinct().subquery('accessible_tree_ids')
            query = db.query(Tree).join(accessible_tree_ids_sq, Tree.id == accessible_tree_ids_sq.c.tree_id)

        if not hasattr(Tree, sort_by or ""): # Ensure sort_by is not None before hasattr
            logger.warning(f"Invalid or missing sort_by column '{sort_by}' for Tree. Defaulting to 'name'.")
            sort_by = "name"
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'
            
        paginated_result = paginate_query(query, Tree, current_page, current_per_page, config.PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
        logger.info(f"Found {paginated_result['total_items']} trees for user {user_id}")
        return paginated_result
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "fetching user trees", db)
    except Exception as e:
        logger.error("Unexpected error fetching user trees.", user_id=user_id, exc_info=True)
        abort(500, "Error fetching user trees.")
    return {}

def update_tree_db(db: DBSession, tree_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Updating tree", tree_id=tree_id, data_keys=list(tree_data.keys()))
    tree = _get_or_404(db, Tree, tree_id)
    # Removed 'is_public', added 'privacy_setting'
    allowed_fields = ['name', 'description', 'default_privacy_level', 'privacy_setting'] 
    validation_errors = {}

    try:
        for key, value in tree_data.items():
            if key in allowed_fields:
                if key == 'default_privacy_level':
                    try: setattr(tree, key, PrivacyLevelEnum(value))
                    except ValueError: validation_errors[key] = f"Invalid value: {value}"
                elif key == 'privacy_setting':
                    try: setattr(tree, key, TreePrivacySettingEnum(value))
                    except ValueError: validation_errors[key] = f"Invalid value: {value}"
                # elif key == 'is_public': # Logic for is_public removed
                #     pass 
                else: 
                    setattr(tree, key, value)
        
        if validation_errors:
            abort(400, description={"message": "Validation failed", "details": validation_errors})

        db.commit(); db.refresh(tree)
        logger.info("Tree updated.", tree_id=tree.id)
        return tree.to_dict()
    # Removed specific ValueError for default_privacy_level, handled by common validation_errors
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "updating tree", db)
    except HTTPException: # Re-raise aborts from validation
        raise
    except Exception as e: # Catch any other unexpected errors
        db.rollback(); logger.error("Unexpected error updating tree.", tree_id=tree_id, exc_info=True)
        abort(500, "Error updating tree.")
    return {}

def delete_tree_db(db: DBSession, tree_id: uuid.UUID) -> None:
    logger.info("Deleting tree", tree_id=tree_id)
    tree = _get_or_404(db, Tree, tree_id)
    try:
        db.delete(tree); db.commit()
        logger.info("Tree deleted.", tree_id=tree_id)
    except IntegrityError as ie:
        db.rollback(); logger.error(f"Integrity error deleting tree {tree_id}.", exc_info=True)
        _handle_sqlalchemy_error(ie, "deleting tree (integrity)", db)
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "deleting tree", db)
    except Exception as e:
        db.rollback(); logger.error("Unexpected error deleting tree.", tree_id=tree_id, exc_info=True)
        abort(500, "Error deleting tree.")

def get_tree_data_for_visualization_db(db: DBSession, tree_id: uuid.UUID) -> Dict[str, Any]:
    logger.info("Fetching full tree data for visualization", tree_id=tree_id)
    _get_or_404(db, Tree, tree_id) 
    try:
        people_list = db.query(Person).filter(Person.tree_id == tree_id).all()
        relationships_list = db.query(Relationship).filter(Relationship.tree_id == tree_id).all()
        num_people = len(people_list); num_relationships = len(relationships_list)
        if num_people > 1000 or num_relationships > 2000:
            logger.warning(f"Fetching large tree for viz: {num_people}p, {num_relationships}r for tree {tree_id}.")
        nodes = []
        for p in people_list:
            label = f"{p.first_name or ''} {p.last_name or ''}".strip()
            if p.nickname: label += f" ({p.nickname})"
            if not label.strip(): label = f"Person (ID: {str(p.id)[:8]})"
            nodes.append({"id": str(p.id), "type": "personNode", "position": {"x": 0, "y": 0},
                "data": {"id": str(p.id), "label": label, "full_name": f"{p.first_name or ''} {p.last_name or ''}".strip(),
                    "gender": p.gender, "dob": p.birth_date.isoformat() if p.birth_date else None,
                    "dod": p.death_date.isoformat() if p.death_date else None, "is_living": p.is_living,}})
        links = []
        for r in relationships_list:
            links.append({"id": str(r.id), "source": str(r.person1_id), "target": str(r.person2_id),
                "type": "customEdge", "label": r.relationship_type.value.replace("_", " ").title(),
                "data": r.to_dict()})
        logger.info("Full tree data fetched for viz.", tree_id=tree_id, nodes=len(nodes), links=len(links))
        return {"nodes": nodes, "links": links}
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, f"fetching tree data for tree {tree_id}", db)
    except Exception as e:
        logger.error("Unexpected error fetching tree data for viz.", tree_id=tree_id, exc_info=True)
        abort(500, "Error fetching tree data for visualization.")
    return {}


def upload_tree_cover_image_db(db: DBSession, tree_id: uuid.UUID, user_id: uuid.UUID, 
                               file_stream, filename: str, content_type: str) -> Dict[str, Any]:
    """
    Uploads a cover image for a tree, saves it to object storage,
    and updates the tree's cover_image_url with the object key.
    """
    logger.info("Attempting to upload tree cover image", tree_id=tree_id, user_id=user_id, filename=filename)
    
    tree = _get_or_404(db, Tree, tree_id)

    # Authorization check: Only the tree creator can change the cover image for now.
    if tree.created_by != user_id:
        logger.warning("User is not authorized to upload cover image for this tree.",
                       tree_id=tree_id, user_id=user_id, tree_owner=tree.created_by)
        abort(403, description="You are not authorized to change the cover image for this tree.")

    try:
        s3_client = get_storage_client()
        if not s3_client:
             logger.error("S3 client not available for tree cover image upload.", tree_id=tree_id)
             abort(500, description="Storage service is currently unavailable.")

        if not create_bucket_if_not_exists(s3_client, config.OBJECT_STORAGE_BUCKET_NAME):
            logger.error("Bucket could not be verified or created for tree cover image upload.",
                         bucket_name=config.OBJECT_STORAGE_BUCKET_NAME)
            abort(500, description="Storage bucket is not ready.")

        secured_filename = secure_filename(filename)
        file_extension = os.path.splitext(secured_filename)[1]
        object_key = f"tree_cover_images/{tree_id}/{uuid.uuid4()}{file_extension}"
        
        logger.debug(f"Uploading tree cover to S3: bucket='{config.OBJECT_STORAGE_BUCKET_NAME}', key='{object_key}'")

        s3_client.upload_fileobj(
            file_stream,
            config.OBJECT_STORAGE_BUCKET_NAME,
            object_key,
            ExtraArgs={'ContentType': content_type}
        )
        
        old_object_key = tree.cover_image_url
        if old_object_key and old_object_key != object_key:
            try:
                logger.info(f"Deleting old tree cover image from S3: {old_object_key}", tree_id=tree_id)
                s3_client.delete_object(Bucket=config.OBJECT_STORAGE_BUCKET_NAME, Key=old_object_key)
            except ClientError as e:
                logger.error(f"Failed to delete old tree cover image {old_object_key} from S3.",
                             error=str(e), tree_id=tree_id)
                # Non-critical error, proceed with updating the new image URL

        tree.cover_image_url = object_key
        db.commit()
        db.refresh(tree)
        
        logger.info("Tree cover image uploaded and record updated successfully.",
                    tree_id=tree_id, object_key=object_key)
        return tree.to_dict()

    except S3UploadFailedError as e:
        db.rollback()
        logger.error("S3 upload failed for tree cover image.", tree_id=tree_id, error=str(e), exc_info=True)
        abort(500, description="Failed to upload tree cover image to storage.")
    except ClientError as e:
        db.rollback()
        logger.error("Boto3 client error during tree cover image upload.", tree_id=tree_id, error=str(e), exc_info=True)
        abort(500, description="A storage service error occurred during tree cover image upload.")
    except SQLAlchemyError as e:
        db.rollback()
        _handle_sqlalchemy_error(e, f"updating tree cover_image_url for tree ID {tree_id}", db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during tree cover image upload.", tree_id=tree_id, error=str(e), exc_info=True)
        abort(500, description="An unexpected error occurred while processing the tree cover image.")
    return {}
