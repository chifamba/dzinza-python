# backend/blueprints/__init__.py
# This file makes the 'blueprints' directory a Python package.

# Import blueprints to make them available for registration
from .auth import auth_bp
from .trees import trees_bp
from .people import people_bp
from .relationships import relationships_bp
from .admin import admin_bp
from .health import health_bp

# You could also define a list of all blueprints here if preferred
# ALL_BLUEPRINTS = [auth_bp, trees_bp, ...]
