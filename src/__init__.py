# This file makes src a Python package and ensures models are imported
from . import user, child, shift, event, shift_pattern, residency_period, album, photo
# Import models so Base.metadata is populated when create_tables is called
from . import grocery

# Import manager modules for convenience (optional)
from . import auth, shift_manager, child_manager, event_manager, shift_pattern_manager, grocery_manager
