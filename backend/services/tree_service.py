# backend/services/tree_service.py
import uuid
import structlog
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_
from flask import abort

from backend.models import Tree, TreeAccess, Person, Relationship, PrivacyLevelEnum
from backend.utils import _get_or_404, _handle_sqlalchemy_error, paginate_query
from backend import config as app_config_module

logger = structlog.get_logger(__name__)

def create_tree_db(db: DBSession, user_id: uuid.UUID, tree_data: Dict[str, Any]) -> Dict[str, Any]:
    tree_name = tree_data.get('name')
    logger.info("Creating new tree", user_id=user_id, tree_name=tree_name)
    if not tree_name: abort(400, "Tree name is required.")
    try: default_privacy_enum = PrivacyLevelEnum(tree_data.get('default_privacy_level', PrivacyLevelEnum.private.value))
    except ValueError: abort(400, f"Invalid default_privacy_level: {tree_data.get('default_privacy_level')}.")
    cover_image_url = tree_data.get('cover_image_url')
    try:
        new_tree = Tree(name=tree_name, description=tree_data.get('description'), created_by=user_id,
            is_public=bool(tree_data.get('is_public', False)), default_privacy_level=default_privacy_enum,
            cover_image_url=cover_image_url)
        db.add(new_tree); db.flush()
        tree_access = TreeAccess(tree_id=new_tree.id, user_id=user_id, access_level='admin', granted_by=user_id)
        db.add(tree_access); db.commit(); db.refresh(new_tree)
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
    cfg_pagination = app_config_module.config.PAGINATION_DEFAULTS
    if page == -1: page = cfg_pagination["page"]
    if per_page == -1: per_page = cfg_pagination["per_page"]
    logger.info("Fetching trees for user", user_id=user_id, page=page, per_page=per_page)
    try:
        owned_trees_sq = db.query(Tree.id.label("tree_id")).filter(Tree.created_by == user_id)
        shared_trees_sq = db.query(TreeAccess.tree_id.label("tree_id")).filter(TreeAccess.user_id == user_id)
        accessible_tree_ids_sq = owned_trees_sq.union(shared_trees_sq).distinct().subquery('accessible_tree_ids')
        query = db.query(Tree).join(accessible_tree_ids_sq, Tree.id == accessible_tree_ids_sq.c.tree_id)
        if not hasattr(Tree, sort_by or ""):
            logger.warning(f"Invalid sort_by '{sort_by}' for Tree. Defaulting to 'name'.")
            sort_by = "name"
        paginated_result = paginate_query(query, Tree, page, per_page, cfg_pagination["max_per_page"], sort_by, sort_order)
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
    allowed_fields = ['name', 'description', 'is_public', 'default_privacy_level', 'cover_image_url']
    try:
        for key, value in tree_data.items():
            if key in allowed_fields:
                if key == 'default_privacy_level': setattr(tree, key, PrivacyLevelEnum(value))
                elif key == 'is_public': setattr(tree, key, bool(value))
                else: setattr(tree, key, value)
        db.commit(); db.refresh(tree)
        logger.info("Tree updated.", tree_id=tree.id)
        return tree.to_dict()
    except ValueError as ve: abort(400, f"Invalid value for default_privacy_level: {tree_data.get('default_privacy_level')}. Error: {ve}")
    except SQLAlchemyError as e: _handle_sqlalchemy_error(e, "updating tree", db)
    except Exception as e:
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
