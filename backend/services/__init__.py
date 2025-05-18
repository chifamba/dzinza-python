# backend/services/__init__.py
"""
This file makes the 'services' directory a Python package.
It can optionally be used to expose service functions for cleaner imports.
"""
# For cleaner imports in blueprints, you can expose service functions here,
# but direct imports from service modules are also fine.

# Example (optional):
# from .user_service import (
#     register_user_db, authenticate_user_db, get_all_users_db,
#     request_password_reset_db, reset_password_db,
#     update_user_role_db, delete_user_db
# )
# from .tree_service import (
#     create_tree_db, get_user_trees_db, update_tree_db, delete_tree_db,
#     get_tree_data_for_visualization_db
# )
# from .person_service import (
#     get_all_people_db, get_person_db, create_person_db,
#     update_person_db, delete_person_db
# )
# from .relationship_service import (
#     get_all_relationships_db, get_relationship_db, create_relationship_db,
#     update_relationship_db, delete_relationship_db
# )
# from .activity_service import get_activity_log_db

# If you do the above, then in blueprints you can do:
# from services import register_user_db
# Instead of:
# from services.user_service import register_user_db

# For now, keeping it simple and letting blueprints import directly from service modules.
