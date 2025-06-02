# backend/blueprints/__init__.py
# This file makes 'blueprints' a Python package.

# Import blueprints to make them available for registration by the app factory
from .auth import auth_bp
from .trees import trees_bp
from .people import people_bp
from .relationships import relationships_bp
from .admin import admin_bp
from .health import health_bp
from .tree_layouts import tree_layouts_bp

# Optional: A list of all blueprints for easier registration in app.py
# ALL_BLUEPRINTS = (
#     auth_bp,
#     trees_bp,
#     people_bp,
#     relationships_bp,
#     admin_bp,
#     health_bp,
# )
