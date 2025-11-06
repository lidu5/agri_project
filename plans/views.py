"""
Views for the plans app.

This file imports all views from separate modules for better organization.
The views are split into logical modules:
- base.py: Utility functions and base classes
- dashboard.py: Dashboard and overview views
- units.py: Unit management views
- indicators.py: Indicator management views
- annual_plans.py: Annual plan management views
- quarterly_reports.py: Quarterly report management views
- api.py: API endpoints for AJAX
- audit.py: Audit and reporting views
- import_export.py: Import/export functionality
"""

# Import all views from the views package
from .views import *