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


from models import Tree, TreeAccess, Person, Relationship, PrivacyLevelEnum, TreePrivacySettingEnum, User, UserRole, PersonTreeAssociation, Event # Added User, UserRole, PersonTreeAssociation, Event
from utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from config import config # Direct import of the config instance
# import config as app_config_module # Keep this if used by get_user_trees_db's cfg_pagination
from storage_client import get_storage_client, create_bucket_if_not_exists
from services.person_service import get_all_people_db as get_persons_in_tree_db # For fetching persons in a tree


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
    _get_or_404(db, Tree, tree_id)  # Ensure tree exists

    try:
        # 1. Get all persons associated with this tree_id using the (imported) service function
        #    This function handles pagination, but for visualization, we usually need all persons.
        #    Assuming get_persons_in_tree_db can return all if page/per_page are specific values,
        #    or we fetch with a very large per_page. For simplicity, let's assume it gets all relevant Person objects.
        #    The imported function already returns a dict like {'items': [Person.to_dict(), ...], ...}
        #    We need the actual Person objects or at least their IDs.
        #    Let's adjust to get Person objects directly if possible, or process IDs from dicts.
        
        # Using a direct query here for clarity on getting Person objects for the tree
        persons_in_tree_query = db.query(Person).join(PersonTreeAssociation).filter(PersonTreeAssociation.tree_id == tree_id)
        people_list = persons_in_tree_query.all()
        
        person_ids_in_tree = {p.id for p in people_list}

        if not person_ids_in_tree:
            logger.info("No persons found in this tree for visualization.", tree_id=tree_id)
            return {"nodes": [], "links": [], "events": []} # Include events key for consistency

        num_people = len(people_list)
        if num_people > 1000: # Adjust threshold as needed
            logger.warning(f"Fetching large tree for viz: {num_people} persons for tree {tree_id}.")

        # 2. Construct nodes for persons in this tree
        nodes = []
        for p in people_list:
            label = f"{p.first_name or ''} {p.last_name or ''}".strip()
            if p.nickname: label += f" ({p.nickname})"
            if not label.strip(): label = f"Person (ID: {str(p.id)[:8]})"
            nodes.append({
                "id": str(p.id), "type": "personNode", "position": {"x": 0, "y": 0}, # Position can be set by frontend
                "data": {
                    "id": str(p.id), "label": label, 
                    "full_name": f"{p.first_name or ''} {p.last_name or ''}".strip(),
                    "gender": p.gender, 
                    "dob": p.birth_date.isoformat() if p.birth_date else None,
                    "dod": p.death_date.isoformat() if p.death_date else None, 
                    "is_living": p.is_living,
                    # Add any other person details needed for the node
                }
            })

        # 3. Fetch all GLOBAL relationships involving these persons
        # A relationship is relevant if EITHER person1_id OR person2_id is in our set of person_ids_in_tree
        relationships_query = db.query(Relationship).filter(
            or_(Relationship.person1_id.in_(person_ids_in_tree), Relationship.person2_id.in_(person_ids_in_tree))
        )
        all_relevant_relationships = relationships_query.all()

        # 4. Filter relationships to only include those where BOTH persons are in the current tree context for visualization
        links = []
        for r in all_relevant_relationships:
            if r.person1_id in person_ids_in_tree and r.person2_id in person_ids_in_tree:
                links.append({
                    "id": str(r.id), "source": str(r.person1_id), "target": str(r.person2_id),
                    "type": "customEdge", # Or determine dynamically based on r.relationship_type
                    "label": r.relationship_type.value.replace("_", " ").title(),
                    "data": r.to_dict() # Relationship.to_dict() no longer has tree_id
                })
        
        # 5. Fetch all GLOBAL events for persons in this tree
        # Event model no longer has tree_id
        events_query = db.query(Event).filter(Event.person_id.in_(person_ids_in_tree))
        event_list_for_tree_persons = events_query.all()
        
        # Prepare events data for the response (optional, but good for consistency)
        events_data = [event.to_dict() for event in event_list_for_tree_persons]

        logger.info("Full tree data fetched for viz.", tree_id=tree_id, nodes_count=len(nodes), links_count=len(links), events_count=len(events_data))
        return {"nodes": nodes, "links": links, "events": events_data} # Added events to response

    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, f"fetching tree data for visualization for tree {tree_id}", db)
    except Exception as e:
        logger.error("Unexpected error fetching tree data for visualization.", tree_id=tree_id, exc_info=True)
        abort(500, "Error fetching tree data for visualization.")
    return {} # Should be unreachable

# --- New functions for Person-Tree association ---

def add_person_to_tree_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID, current_user_id: uuid.UUID) -> Dict[str, Any]:
    """Adds a person to a tree by creating an association in PersonTreeAssociation."""
    logger.info("Attempting to add person to tree", person_id=person_id, tree_id=tree_id, current_user_id=current_user_id)

    # Authorization: Check if current_user_id has rights to modify the tree
    # (e.g., is tree creator or has 'admin' access in TreeAccess)
    tree = _get_or_404(db, Tree, tree_id)
    if tree.created_by != current_user_id:
        access = db.query(TreeAccess).filter_by(tree_id=tree_id, user_id=current_user_id, access_level='admin').one_or_none()
        if not access:
            logger.warning("User not authorized to add person to tree", tree_id=tree_id, current_user_id=current_user_id)
            abort(403, description="You are not authorized to add people to this tree.")

    # Check if person exists (globally)
    _get_or_404(db, Person, person_id)

    # Check if association already exists
    existing_association = db.query(PersonTreeAssociation).filter_by(person_id=person_id, tree_id=tree_id).one_or_none()
    if existing_association:
        logger.info("Person already associated with tree", person_id=person_id, tree_id=tree_id)
        # Consider returning a specific message or the existing association dict
        return {"message": "Person already associated with this tree.", "association_id": None} # No ID for composite PK model

    try:
        new_association = PersonTreeAssociation(person_id=person_id, tree_id=tree_id)
        db.add(new_association)
        db.commit()
        # For composite PK models, there's no single 'id'. Return relevant info.
        logger.info("Person successfully added to tree", person_id=person_id, tree_id=tree_id)
        return {"person_id": str(person_id), "tree_id": str(tree_id), "message": "Person added to tree successfully"}
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, "adding person to tree", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error adding person to tree.", person_id=person_id, tree_id=tree_id, exc_info=True)
        abort(500, "Error adding person to tree.")
    return {} # Should be unreachable

def remove_person_from_tree_db(db: DBSession, person_id: uuid.UUID, tree_id: uuid.UUID, current_user_id: uuid.UUID) -> bool:
    """Removes a person's association from a tree."""
    logger.info("Attempting to remove person from tree", person_id=person_id, tree_id=tree_id, current_user_id=current_user_id)

    # Authorization (similar to add_person_to_tree_db)
    tree = _get_or_404(db, Tree, tree_id)
    if tree.created_by != current_user_id:
        access = db.query(TreeAccess).filter_by(tree_id=tree_id, user_id=current_user_id, access_level='admin').one_or_none()
        if not access:
            logger.warning("User not authorized to remove person from tree", tree_id=tree_id, current_user_id=current_user_id)
            abort(403, description="You are not authorized to remove people from this tree.")
    
    association = db.query(PersonTreeAssociation).filter_by(person_id=person_id, tree_id=tree_id).one_or_none()
    if not association:
        logger.warning("Person-tree association not found for removal.", person_id=person_id, tree_id=tree_id)
        abort(404, description="Person is not associated with this tree.")

    try:
        db.delete(association)
        db.commit()
        logger.info("Person successfully removed from tree", person_id=person_id, tree_id=tree_id)
        return True
    except SQLAlchemyError as e:
        _handle_sqlalchemy_error(e, "removing person from tree", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error removing person from tree.", person_id=person_id, tree_id=tree_id, exc_info=True)
        abort(500, "Error removing person from tree.")
    return False # Should be unreachable


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
