# backend/blueprints/people.py
import uuid
import structlog
from flask import Blueprint, request, jsonify, g, session, abort
from werkzeug.exceptions import HTTPException

from decorators import require_tree_access
from services.person_service import (
    get_all_people_db, get_person_db, create_person_db,
    update_person_db, delete_person_db
)
from utils import get_pagination_params

logger = structlog.get_logger(__name__)
people_bp = Blueprint('people_api', __name__, url_prefix='/api/people')

@people_bp.route('', methods=['GET'])
@require_tree_access('view')
def get_all_people_endpoint():
    db = g.db; tree_id = g.active_tree_id
    page, per_page, sort_by, sort_order = get_pagination_params()
    sort_by = sort_by or "last_name"
    filters = {}
    if request.args.get('is_living') is not None: filters['is_living'] = request.args.get('is_living', type=str).lower() == 'true'
    if request.args.get('name_contains'): filters['name_contains'] = request.args.get('name_contains', type=str)
    logger.info("Get all people", tree_id=tree_id, page=page, per_page=per_page, filters=filters)
    try:
        return jsonify(get_all_people_db(db, tree_id, page, per_page, sort_by, sort_order, filters=filters)), 200
    except Exception as e:
        logger.error("Error in get_all_people.", tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching people.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['GET'])
@require_tree_access('view')
def get_person_endpoint(person_id_param: uuid.UUID):
    db = g.db; tree_id = g.active_tree_id
    logger.info("Get person", person_id=person_id_param, tree_id=tree_id)
    try:
        return jsonify(get_person_db(db, person_id_param, tree_id)), 200
    except Exception as e:
        logger.error("Error in get_person.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error fetching person details.")
        raise

@people_bp.route('', methods=['POST'])
@require_tree_access('edit')
def create_person_endpoint():
    data = request.get_json(); user_id = uuid.UUID(session['user_id'])
    if not data: abort(400, "Request body cannot be empty.")
    db = g.db; tree_id = g.active_tree_id
    logger.info("Create person", tree_id=tree_id, user_id=user_id, data_keys=list(data.keys()))
    try:
        return jsonify(create_person_db(db, user_id, tree_id, data)), 201
    except Exception as e:
        logger.error("Error in create_person.", tree_id=tree_id, user_id=user_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error creating person.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['PUT'])
@require_tree_access('edit')
def update_person_endpoint(person_id_param: uuid.UUID):
    data = request.get_json()
    if not data: abort(400, "Request body cannot be empty.")
    db = g.db; tree_id = g.active_tree_id
    logger.info("Update person", person_id=person_id_param, tree_id=tree_id, data_keys=list(data.keys()))
    try:
        return jsonify(update_person_db(db, person_id_param, tree_id, data)), 200
    except Exception as e:
        logger.error("Error in update_person.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error updating person.")
        raise

@people_bp.route('/<uuid:person_id_param>', methods=['DELETE'])
@require_tree_access('edit')
def delete_person_endpoint(person_id_param: uuid.UUID):
    db = g.db; tree_id = g.active_tree_id
    logger.info("Delete person", person_id=person_id_param, tree_id=tree_id)
    try:
        delete_person_db(db, person_id_param, tree_id)
        return '', 204
    except Exception as e:
        logger.error("Error in delete_person.", person_id=person_id_param, tree_id=tree_id, exc_info=True)
        if not isinstance(e, HTTPException): abort(500, "Error deleting person.")
        raise
