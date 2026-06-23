# routes/__init__.py
# This file makes the routes directory a Python package
# Import all blueprints here for easier registration

from .auth import auth_bp
from .users import users_bp
from .dashboard import dashboard_bp
from .health import health_bp
from .notifications import notifications_bp
from .appointments import appointments_bp
from .tracker import tracker_bp
from .hospitals import hospitals_bp
from .donations import donations_bp
from .emergencies import emergencies_bp
from .navigation import navigation_bp

# List all blueprints for easy registration
blueprints = [
    auth_bp,
    users_bp,
    dashboard_bp,
    health_bp,
    notifications_bp,
    appointments_bp,
    tracker_bp,
    hospitals_bp,
    donations_bp,
    emergencies_bp,
    navigation_bp
]