"""
Views package for the plans app.
This file imports all views from the separate modules for easy access.
"""

# Import all views from separate modules
from .base import get_user_profile, can_user_access_unit, log_workflow_action

# Dashboard views
# from .dashboard import dashboard, performance_summary
from .dashboard import DashboardViewSet


# Unit management views
from .units import UnitViewSet 

# Indicator management views
from .indicators import IndicatorViewSet

# Annual plan views
from .annual_plans import AnnualPlanViewSet
# Quarterly report views
from .quarterly_reports import QuarterlyReportViewSet

# API views
from .api import (
    get_indicators_for_unit, get_annual_plan_progress, get_unit_statistics,
    get_quarterly_progress, validate_indicator_code, get_dashboard_data,
    get_recent_activities
)

# Audit views
from .audit import AuditViewSet

# Import/Export views
from .import_export import ImportExportViewSet
# Make all views available at the package level
__all__ = [
    # Base utilities
    'get_user_profile', 'can_user_access_unit', 'log_workflow_action', 'BaseViewMixin',
    
    # Dashboard
    'dashboard', 'performance_summary',
    
    # Units
    'UnitListView', 'UnitDetailView',
    
    # Indicators
    'IndicatorListView', 'IndicatorCreateView', 'IndicatorUpdateView',
    
    # Annual Plans
    'AnnualPlanListView', 'AnnualPlanDetailView', 'AnnualPlanCreateView',
    'submit_annual_plan', 'approve_annual_plan', 'reject_annual_plan',
    'annual_plan_targets', 'delete_annual_plan_target', 'export_annual_plan',
    
    # Quarterly Reports
    'QuarterlyReportListView', 'QuarterlyReportDetailView', 'QuarterlyReportCreateView',
    'submit_quarterly_report', 'approve_quarterly_report',
    'quarterly_report_entries', 'delete_quarterly_report_entry', 'export_quarterly_report',
    
    # API
    'get_indicators_for_unit', 'get_annual_plan_progress', 'get_unit_statistics',
    'get_quarterly_progress', 'validate_indicator_code', 'get_dashboard_data',
    'get_recent_activities',
    
    # Audit
    'audit_log', 'audit_performance_summary', 'unit_performance',
    
    # Import/Export
    'import_data', 'export_data', 'export_annual_plans', 'export_quarterly_reports',
    'export_indicators', 'export_audit_log',
]

