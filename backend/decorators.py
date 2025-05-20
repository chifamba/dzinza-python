# backend/decorators.py
import uuid
from functools import wraps
from flask import session, g, abort # current_app not used directly here
import structlog

import models # Absolute import for models module

logger = structlog.get_logger(__name__)

def require_auth(f):
    """Decorator to ensure a user is authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Authentication required: session not found or user_id missing.",
                           session_keys=list(session.keys()))
            abort(401, description="Authentication required. Please log in.")
        
        # Optional: Re-verify user from DB if session validity is short or needs active check
        # db = g.get('db')
        # current_user = db.query(models.User).filter_by(id=session['user_id']).first()
        # if not current_user or not current_user.is_active:
        #     session.clear()
        #     abort(401, description="User account is invalid or inactive.")
        # g.current_user = current_user

        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to ensure the authenticated user has an ADMIN role."""
    @wraps(f)
    @require_auth 
    def decorated_function(*args, **kwargs):
        if session.get('role') != models.UserRole.ADMIN.value: # Use models.UserRole
            logger.warning("Admin access required, but user is not admin.",
                           user_id=session.get('user_id'),
                           user_role=session.get('role'))
            abort(403, description="Administrator access is required for this action.")
        return f(*args, **kwargs)
    return decorated_function

def require_tree_access(level: str = 'view'): 
    """
    Decorator for tree access. Tree ID from 'tree_id_param' in path or 'active_tree_id' in session.
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_id_str = session.get('user_id')
            try:
                user_id = uuid.UUID(user_id_str)
            except (ValueError, TypeError):
                logger.error("Invalid user_id format in session for tree access.", user_id_session=user_id_str)
                abort(401, "Invalid session data.")

            tree_id_str_from_path = kwargs.get('tree_id_param') # From URL like /trees/<uuid:tree_id_param>/...
            tree_id_to_check_str = str(tree_id_str_from_path) if tree_id_str_from_path else session.get('active_tree_id')
            
            if not tree_id_to_check_str:
                logger.warning("Tree access required, but no tree_id context.", user_id=user_id, route=f.__name__)
                abort(400, description={"message": "No active tree selected or tree ID provided.", "code": "NO_TREE_CONTEXT"})
            
            try:
                tree_id = uuid.UUID(tree_id_to_check_str)
            except ValueError:
                 logger.warning("Tree access check: Invalid UUID for tree_id.", user_id=user_id, input_tree_id=tree_id_to_check_str)
                 if tree_id_to_check_str == session.get('active_tree_id'): session.pop('active_tree_id', None)
                 abort(400, description={"message": "Invalid tree ID format.", "code": "INVALID_TREE_ID_FORMAT"})

            db = g.get('db')
            if not db:
                logger.error("Database session not found in g for @require_tree_access.")
                abort(500, "Internal server error during access check.")

            # Use models.Tree and models.TreeAccess from the imported models module
            tree = db.query(models.Tree).filter(models.Tree.id == tree_id).one_or_none()
            if not tree:
                logger.warning("Tree access check failed: Tree not found in DB.", user_id=user_id, tree_id=tree_id)
                if tree_id_to_check_str == session.get('active_tree_id'): session.pop('active_tree_id', None)
                abort(404, description=f"Tree with ID {tree_id} not found.")

            has_permission = False
            actual_access_level = None # This will store the determined access level as string ('view', 'edit', 'admin')

            # 1. Check for public tree access (only for 'view' level)
            if tree.privacy_setting == models.TreePrivacySettingEnum.PUBLIC and level == 'view':
                has_permission = True
                actual_access_level = 'view' # Granted 'view' due to public setting
            
            # 2. If not granted by public setting, check ownership or TreeAccess table
            if not has_permission:
                if tree.created_by == user_id:
                    actual_access_level = 'admin' # Owner is always admin
                else:
                    tree_access_entry = db.query(models.TreeAccess).filter(
                        models.TreeAccess.tree_id == tree_id, models.TreeAccess.user_id == user_id
                    ).one_or_none()
                    if tree_access_entry:
                        actual_access_level = tree_access_entry.access_level
            
            # if not actual_access_level and tree.is_public: # Old logic using is_public, now handled by privacy_setting
            #     actual_access_level = 'view'

            access_hierarchy = {'view': 1, 'edit': 2, 'admin': 3} # Higher value means more permission
            required_level_val = access_hierarchy.get(level, 0) 
            granted_level_val = access_hierarchy.get(actual_access_level or "", 0) # Default to 0 if actual_access_level is None

            if granted_level_val >= required_level_val:
                has_permission = True
            
            if not has_permission: # This check now correctly uses the potentially updated has_permission
                logger.warning("Tree access denied.", user_id=user_id, tree_id=tree_id,
                               required_level=level, granted_level=actual_access_level or "none",
                               tree_privacy=tree.privacy_setting.value)
                abort(403, description={
                    "message": f"You do not have sufficient permissions ('{level}' required) for this tree.",
                    "code": "ACCESS_DENIED_TREE"
                })
            
            g.active_tree = tree
            g.active_tree_id = tree_id 
            g.tree_access_level = actual_access_level # Store the determined access level
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
