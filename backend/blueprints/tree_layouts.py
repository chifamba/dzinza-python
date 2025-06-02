from flask import Blueprint, request, jsonify, g # Import g for db session
from backend.services.tree_layout_service import TreeLayoutService
# Assuming TreeLayout model might still be needed for type hinting or direct use cases elsewhere,
# but service layer should be primary interface.
from backend.models import TreeLayout
import structlog

logger = structlog.get_logger(__name__)

tree_layouts_bp = Blueprint('tree_layouts', __name__, url_prefix='/api/tree_layouts')

# Helper to get service instance with current db session
def get_service():
    # g.db should be populated by a @app.before_request hook
    if not hasattr(g, 'db'):
        logger.error("Database session not found in g. Service cannot be initialized.")
        # This situation should ideally not happen if before_request is set up correctly.
        # Handle gracefully or raise an exception. For now, returning None or error.
        return None
    return TreeLayoutService(db_session=g.db)

@tree_layouts_bp.route('', methods=['POST'])
def save_or_update_tree_layout():
    service = get_service()
    if not service:
        return jsonify({'error': 'Internal server error: DB session not available'}), 500

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user_id = data.get('user_id') # In a real app, this should come from authenticated user (e.g., current_user.id)
    tree_id = data.get('tree_id')
    layout_data = data.get('layout_data')

    if not all([user_id, tree_id, layout_data]):
        return jsonify({'error': 'Missing required fields: user_id, tree_id, layout_data'}), 400

    # Convert to string if they are not, as service expects strings for UUIDs
    user_id_str = str(user_id)
    tree_id_str = str(tree_id)

    try:
        layout = service.create_or_update_layout(user_id=user_id_str, tree_id=tree_id_str, layout_data=layout_data)
        if layout:
            # Determine if it was a create or update for the message, though service handles this logic.
            # For simplicity, a generic success message.
            # We can check layout.created_at vs layout.updated_at if specific messages are needed.
            return jsonify({'message': 'Tree layout saved successfully', 'layout': layout.to_dict()}), 200 # 200 for update, 201 for create
        else:
            # This path might be taken if service internally decides not to create/update (e.g. validation error)
            # or if an error occurred that the service logged but returned None.
            return jsonify({'error': 'Failed to save tree layout'}), 500
    except Exception as e:
        logger.error("Error in save_or_update_tree_layout blueprint", error=str(e), exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@tree_layouts_bp.route('/<tree_id>/<user_id>', methods=['GET'])
def get_tree_layout_route(tree_id: str, user_id: str): # Type hint for clarity
    service = get_service()
    if not service:
        return jsonify({'error': 'Internal server error: DB session not available'}), 500

    # Ensure user_id from URL is used, not from a potentially different authenticated user if rules are strict.
    # In many apps, you'd verify current_user.id == user_id for this kind of direct object access.

    # Convert to string as service expects strings for UUIDs
    user_id_str = str(user_id)
    tree_id_str = str(tree_id)

    layout = service.get_layout(user_id=user_id_str, tree_id=tree_id_str)

    if not layout:
        return jsonify({'error': 'Layout not found or access denied'}), 404

    return jsonify(layout.to_dict()), 200

@tree_layouts_bp.route('/<tree_id>/<user_id>', methods=['DELETE'])
def delete_tree_layout_route(tree_id: str, user_id: str): # Type hint
    service = get_service()
    if not service:
        return jsonify({'error': 'Internal server error: DB session not available'}), 500

    # Similar to GET, ensure the user_id from URL is appropriate,
    # possibly checking against authenticated user.
    user_id_str = str(user_id)
    tree_id_str = str(tree_id)

    success = service.delete_layout(user_id=user_id_str, tree_id=tree_id_str)

    if success:
        return jsonify({'message': 'Tree layout deleted successfully'}), 200
    else:
        # This could be because layout didn't exist or a DB error occurred.
        # Service logs specifics.
        return jsonify({'error': 'Failed to delete layout or layout not found'}), 404 # Or 500 if it implies an error beyond "not found"
