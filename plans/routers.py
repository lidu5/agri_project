"""
Django REST Framework router configuration for the plans app.
"""
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views.dashboard import DashboardViewSet
from .views.units import UnitViewSet
from .views.indicators import IndicatorViewSet
from .views.annual_plans import AnnualPlanViewSet, AnnualPlanTargetViewSet
from .views.quarterly_reports import QuarterlyReportViewSet, QuarterlyIndicatorEntryViewSet
from .views.audit import AuditViewSet
from .views.import_export import ImportExportViewSet

# Create the main router
router = DefaultRouter()

# Register main viewsets
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'units', UnitViewSet, basename='units')
router.register(r'indicators', IndicatorViewSet, basename='indicators')
router.register(r'annual-plans', AnnualPlanViewSet, basename='annual-plans')
router.register(r'annual-plan-targets', AnnualPlanTargetViewSet, basename='annual-plan-targets')
router.register(r'quarterly-reports', QuarterlyReportViewSet, basename='quarterly-reports')
router.register(r'quarterly-entries', QuarterlyIndicatorEntryViewSet, basename='quarterly-entries')
router.register(r'audit', AuditViewSet, basename='audit')
router.register(r'import-export', ImportExportViewSet, basename='import-export')

# Create nested routers for related resources
units_router = routers.NestedDefaultRouter(router, r'units', lookup='unit')
units_router.register(r'indicators', IndicatorViewSet, basename='unit-indicators')
units_router.register(r'annual-plans', AnnualPlanViewSet, basename='unit-annual-plans')
units_router.register(r'quarterly-reports', QuarterlyReportViewSet, basename='unit-quarterly-reports')

annual_plans_router = routers.NestedDefaultRouter(router, r'annual-plans', lookup='annual_plan')
annual_plans_router.register(r'targets', AnnualPlanTargetViewSet, basename='annual-plan-targets')

quarterly_reports_router = routers.NestedDefaultRouter(router, r'quarterly-reports', lookup='quarterly_report')
quarterly_reports_router.register(r'entries', QuarterlyIndicatorEntryViewSet, basename='quarterly-report-entries')

# Combine all routers
urlpatterns = router.urls + units_router.urls + annual_plans_router.urls + quarterly_reports_router.urls
