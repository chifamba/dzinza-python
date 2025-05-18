# backend/decorators.py
import uuid
from functools import wraps
from flask import session, g, abort, current_app
import structlog

from .models import User, Tree, TreeAccess, UserRole # For type checking and role comparison
# SessionLocal might be needed if g.db is not guaranteed to be set by a before_request hook
# from .database import SessionLocal

logger = structlog.get_logger(__name__)

def require_auth(f):
    """Decorator to ensure a user is authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Authentication required: session not found or user_id missing.",
                           session_keys=list(session.keys()))
            abort(401, description="Authentication required. Please log in.")
        
        # Optional: Verify user exists and is active in DB for every authenticated request
        # This adds DB overhead but increases security against stale sessions.
        # db = g.get('db')
        # if not db:
        #     logger.error("Database session not found in g for @require_auth. This should not happen.")
        #     abort(500, "Internal server error during authentication.")
        # current_user = db.query(User).filter_by(id=session['user_id']).first()
        # if not current_user or not current_user.is_active:
        #     session.clear()
        #     logger.warning("Authentication failed: User not found in DB or inactive.", user_id_from_session=session.get('user_id'))
        #     abort(401, description="User account is invalid or inactive. Please log in again.")
        # g.current_user = current_user # Make user object available in request context

        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to ensure the authenticated user has an ADMIN role."""
    @wraps(f)
    @require_auth # Ensures user is logged in first
    def decorated_function(*args, **kwargs):
        # UserRole.ADMIN.value is 'admin' (string)
        if session.get('role') != UserRole.ADMIN.value:
            logger.warning("Admin access required, but user is not admin.",
                           user_id=session.get('user_id'),
                           user_role=session.get('role'))
            abort(403, description="Administrator access is required for this action.")
        return f(*args, **kwargs)
    return decorated_function

def require_tree_access(level: str = 'view'): # level can be 'view', 'edit', 'admin'
    """
    Decorator to ensure user has the required access level to a tree.
    The tree_id is expected to be passed as a path parameter named 'tree_id_param'
    OR be present in the session as 'active_tree_id'.
    Path parameter takes precedence.
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_id_str = session.get('user_id')
            # @require_auth should ensure user_id_str is present
            try:
                user_id = uuid.UUID(user_id_str)
            except (ValueError, TypeError):
                logger.error("Invalid user_id format in session.", user_id_session=user_id_str)
                abort(401, "Invalid session data.") # Should not happen if login sets it correctly

            # Determine tree_id: from path parameter or active_tree_id in session
            # The route using this decorator must name its tree UUID path param 'tree_id_param'
            # e.g. @app.route('/api/trees/<uuid:tree_id_param>/people')
            tree_id_str_from_path = kwargs.get('tree_id_param')
            
            if tree_id_str_from_path:
                tree_id_to_check_str = str(tree_id_str_from_path) # Ensure it's a string if UUID object
            else:
                tree_id_to_check_str = session.get('active_tree_id')
                if not tree_id_to_check_str:
                    logger.warning("Tree access required, but no tree_id in path and no active_tree_id in session.",
                                   user_id=user_id, called_route=f.__name__)
                    abort(400, description={"message": "No active tree selected or tree ID provided in the path.", "code": "NO_TREE_CONTEXT"})
            
            try:
                tree_id = uuid.UUID(tree_id_to_check_str)
            except ValueError:
                 logger.warning("Tree access check: Invalid UUID format for tree_id.",
                                user_id=user_id, tree_id_input=tree_id_to_check_str)
                 if tree_id_to_check_str == session.get('active_tree_id'):
                     session.pop('active_tree_id', None) # Clear invalid session tree
                 abort(400, description={"message": "Invalid tree ID format.", "code": "INVALID_TREE_ID_FORMAT"})

            db = g.get('db')
            if not db:
                logger.error("Database session not found in g for @require_tree_access. This should not happen.")
                abort(500, "Internal server error during access check.")

            tree = db.query(Tree).filter(Tree.id == tree_id).one_or_none()
            if not tree:
                logger.warning("Tree access check failed: Tree not found in DB.", user_id=user_id, tree_id=tree_id)
                if tree_id_to_check_str == session.get('active_tree_id'):
                    session.pop('active_tree_id', None)
                abort(404, description=f"Tree with ID {tree_id} not found.")

            has_permission = False
            actual_access_level = None

            # 1. Check if user is the owner of the tree (implies admin access)
            if tree.created_by == user_id:
                 actual_access_level = 'admin'
            else:
                # 2. Check TreeAccess table for explicit permissions
                tree_access_entry = db.query(TreeAccess).filter(
                    TreeAccess.tree_id == tree_id,
                    TreeAccess.user_id == user_id
                ).one_or_none()
                if tree_access_entry:
                    actual_access_level = tree_access_entry.access_level
            
            # 3. Check if tree is public (only grants 'view' access)
            if not actual_access_level and tree.is_public: # If no specific access, but tree is public
                actual_access_level = 'view' # Public implies view access

            # Evaluate permission based on hierarchy: admin > edit > view
            access_hierarchy = {'view': 1, 'edit': 2, 'admin': 3}
            required_level_val = access_hierarchy.get(level, 0) # Default to 0 if invalid level string
            granted_level_val = access_hierarchy.get(actual_access_level, 0)

            if granted_level_val >= required_level_val:
                has_permission = True
            
            if not has_permission:
                logger.warning("Tree access denied.", user_id=user_id, tree_id=tree_id,
                               required_level=level, granted_level=actual_access_level or "none")
                abort(403, description={
                    "message": f"You do not have sufficient permissions ({level} required) for this tree.",
                    "code": "ACCESS_DENIED_TREE"
                })
            
            # Store tree object, its ID, and user's access level in g for easy access in the route
            g.active_tree = tree
            g.active_tree_id = tree_id # UUID object
            g.tree_access_level = actual_access_level
            
            # If tree_id came from path, ensure session's active_tree_id is consistent if it's different
            # This is optional behavior, depends on desired UX.
            # if tree_id_str_from_path and session.get('active_tree_id') != str(tree_id):
            #    session['active_tree_id'] = str(tree_id)
            #    logger.info(f"Updated session active_tree_id to {tree_id} based on path parameter.")

            return f(*args, **kwargs)
        return decorated_function
    return decorator
