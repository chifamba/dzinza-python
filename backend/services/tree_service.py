# backend/services/tree_service.py
import uuid
import structlog
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_ # For get_user_trees_db query
from flask import abort

from ..models import Tree, TreeAccess, Person, Relationship, PrivacyLevelEnum
from ..utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from ..config import PAGINATION_DEFAULTS, DEFAULT_PAGE, DEFAULT_PAGE_SIZE
# from opentelemetry import trace

# tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)

def create_tree_db(db: DBSession, user_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new tree and grants owner admin access."""
    tree_name = tree_data.get('name')
    logger.info("Attempting to create new tree", user_id=user_id, tree_name=tree_name)

    if not tree_name:
        abort(400, description="Tree name is required.")
    
    try:
        default_privacy_str = tree_data.get('default_privacy_level', PrivacyLevelEnum.private.value)
        default_privacy_enum = PrivacyLevelEnum(default_privacy_str)
    except ValueError:
        abort(400, description=f"Invalid default_privacy_level: {default_privacy_str}. Valid values: {[p.value for p in PrivacyLevelEnum]}")

    try:
        new_tree = Tree(
            name=tree_name,
            description=tree_data.get('description'),
            created_by=user_id,
            is_public=bool(tree_data.get('is_public', False)),
            default_privacy_level=default_privacy_enum,
        )
        db.add(new_tree)
        db.flush() # Flush to get new_tree.id for TreeAccess

        tree_access = TreeAccess(
             tree_id=new_tree.id, user_id=user_id,
             access_level='admin', granted_by=user_id
        )
        db.add(tree_access)
        db.commit()
        db.refresh(new_tree) # Refresh to get all defaults and relationships loaded
        logger.info("Tree created successfully with owner access.", tree_id=new_tree.id, created_by=user_id)
        return new_tree.to_dict()
    except SQLAlchemyError as e:
        logger.error("Database error during tree creation.", user_id=user_id, exc_info=True)
        _handle_sqlalchemy_error(e, "creating tree", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during tree creation.", user_id=user_id, exc_info=True)
        abort(500, description="An unexpected error occurred during tree creation.")
    return {} # Should be unreachable

def get_user_trees_db(db: DBSession,
                        user_id: uuid.UUID,
                        page: int = DEFAULT_PAGE,
                        per_page: int = DEFAULT_PAGE_SIZE,
                        sort_by: Optional[str] = "name",
                        sort_order: Optional[str] = "asc"
                        ) -> Dict[str, Any]:
    """Fetches paginated trees accessible by the user (owned or shared)."""
    logger.info("Fetching trees for user", user_id=user_id, page=page, per_page=per_page)
    try:
        owned_trees_sq = db.query(Tree.id.label("tree_id")).filter(Tree.created_by == user_id)
        shared_trees_sq = db.query(TreeAccess.tree_id.label("tree_id")).filter(TreeAccess.user_id == user_id)
        accessible_tree_ids_sq = owned_trees_sq.union(shared_trees_sq).distinct().subquery('accessible_tree_ids')
        query = db.query(Tree).join(accessible_tree_ids_sq, Tree.id == accessible_tree_ids_sq.c.tree_id)
        
        if not hasattr(Tree, sort_by or ""):
            logger.warning(f"Invalid sort_by column '{sort_by}' for Tree. Defaulting to 'name'.")
            sort_by = "name"

        paginated_result = paginate_query(query, Tree, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
        logger.info(f"Found {paginated_result['total_items']} trees for user {user_id}")
        return paginated_result
    except SQLAlchemyError as e:
        logger.error("Database error fetching user trees.", user_id=user_id, exc_info=True)
        _handle_sqlalchemy_error(e, "fetching user trees", db)
    except Exception as e:
        logger.error("Unexpected error fetching user trees.", user_id=user_id, exc_info=True)
        abort(500, description="An unexpected error occurred while fetching trees.")
    return {} # Should be unreachable

def update_tree_db(db: DBSession, tree_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates an existing tree."""
    logger.info("Updating tree", tree_id=tree_id, data_keys=list(tree_data.keys()))
    tree = _get_or_404(db, Tree, tree_id)
    
    allowed_fields = ['name', 'description', 'is_public', 'default_privacy_level']
    try:
        for key, value in tree_data.items():
            if key in allowed_fields:
                if key == 'default_privacy_level':
                    setattr(tree, key, PrivacyLevelEnum(value))
                elif key == 'is_public':
                    setattr(tree, key, bool(value))
                else:
                    setattr(tree, key, value)
        
        db.commit()
        db.refresh(tree)
        logger.info("Tree updated successfully", tree_id=tree.id)
        return tree.to_dict()
    except ValueError as ve: # For Enum conversion
        abort(400, description=f"Invalid value for default_privacy_level: {tree_data.get('default_privacy_level')}. Error: {ve}")
    except SQLAlchemyError as e:
        logger.error("Database error during tree update.", tree_id=tree_id, exc_info=True)
        _handle_sqlalchemy_error(e, "updating tree", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during tree update.", tree_id=tree_id, exc_info=True)
        abort(500, description="An unexpected error occurred while updating the tree.")
    return {} # Should be unreachable

def delete_tree_db(db: DBSession, tree_id: uuid.UUID) -> None:
    """Deletes a tree and its associated data (cascades)."""
    logger.info("Deleting tree", tree_id=tree_id)
    tree = _get_or_404(db, Tree, tree_id)
    try:
        # Cascading deletes for People, Relationships, TreeAccess should be handled by DB constraints (ondelete="CASCADE")
        db.delete(tree)
        db.commit()
        logger.info("Tree deleted successfully", tree_id=tree_id)
    except IntegrityError as ie: # Should be rare if cascades are set up correctly
        db.rollback()
        logger.error(f"Integrity error deleting tree {tree_id}, possibly due to FK constraints not cascading.", exc_info=True)
        _handle_sqlalchemy_error(ie, "deleting tree (integrity)", db)
    except SQLAlchemyError as e:
        logger.error("Database error during tree deletion.", tree_id=tree_id, exc_info=True)
        _handle_sqlalchemy_error(e, "deleting tree", db)
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error during tree deletion.", tree_id=tree_id, exc_info=True)
        abort(500, description="An unexpected error occurred while deleting the tree.")


def get_tree_data_for_visualization_db(db: DBSession, tree_id: uuid.UUID) -> Dict[str, Any]:
    """Fetches all people and relationships for a tree, formatted for visualization."""
    logger.info("Fetching full tree data for visualization", tree_id=tree_id)
    _get_or_404(db, Tree, tree_id) # Ensure tree exists, access handled by decorator

    try:
        people_list = db.query(Person).filter(Person.tree_id == tree_id).all()
        relationships_list = db.query(Relationship).filter(Relationship.tree_id == tree_id).all()

        num_people = len(people_list)
        num_relationships = len(relationships_list)
        if num_people > 1000 or num_relationships > 2000:
            logger.warning(f"Fetching large tree for visualization: {num_people} people, {num_relationships} relationships for tree {tree_id}.")

        nodes = []
        for person_obj in people_list:
            label = f"{person_obj.first_name or ''} {person_obj.last_name or ''}".strip()
            if person_obj.nickname: label += f" ({person_obj.nickname})"
            if not label.strip(): label = f"Person (ID: {str(person_obj.id)[:8]})"
            nodes.append({
                "id": str(person_obj.id), "type": "personNode", "position": {"x": 0, "y": 0},
                "data": {
                    "id": str(person_obj.id), "label": label,
                    "full_name": f"{person_obj.first_name or ''} {person_obj.last_name or ''}".strip(),
                    "gender": person_obj.gender,
                    "dob": person_obj.birth_date.isoformat() if person_obj.birth_date else None,
                    "dod": person_obj.death_date.isoformat() if person_obj.death_date else None,
                    "is_living": person_obj.is_living,
                }
            })

        links = []
        for rel_obj in relationships_list:
            links.append({
                "id": str(rel_obj.id), "source": str(rel_obj.person1_id), "target": str(rel_obj.person2_id),
                "type": "customEdge", "label": rel_obj.relationship_type.value.replace("_", " ").title(),
                "data": rel_obj.to_dict()
            })
        
        logger.info("Full tree data fetched for visualization", tree_id=tree_id, num_nodes=len(nodes), num_links=len(links))
        return {"nodes": nodes, "links": links}
    except SQLAlchemyError as e:
        logger.error("Database error fetching tree data for visualization.", tree_id=tree_id, exc_info=True)
        _handle_sqlalchemy_error(e, f"fetching tree data for tree {tree_id}", db)
    except Exception as e:
        logger.error("Unexpected error fetching tree data for visualization.", tree_id=tree_id, exc_info=True)
        abort(500, description="An unexpected error occurred while fetching tree data for visualization.")
    return {} # Should be unreachable
