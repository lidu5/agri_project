"""
Dashboard and overview views for the plans app using Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from ..models import Unit, Indicator, AnnualPlan, QuarterlyReport, WorkflowAudit
from ..serializers import (
    DashboardStatsSerializer, PerformanceSummarySerializer, 
    WorkflowAuditSerializer, AnnualPlanListSerializer
)
from .base import BaseViewSet, get_user_profile


class DashboardViewSet(BaseViewSet):
    """Dashboard API endpoints."""
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics."""
        profile = self.get_user_profile()
        current_year = timezone.now().year
        current_quarter = ((timezone.now().month - 1) // 3) + 1
        
        # Get accessible units
        if profile.role == 'SUPERADMIN':
            accessible_units = Unit.objects.all()
        else:
            accessible_units = Unit.objects.filter(id=profile.unit.id)
        
        # Statistics
        stats = {
            'total_units': accessible_units.count(),
            'total_indicators': Indicator.objects.filter(owner_unit__in=accessible_units).count(),
            'annual_plans_current': AnnualPlan.objects.filter(
                year=current_year,
                unit__in=accessible_units
            ).count(),
            'quarterly_reports_current': QuarterlyReport.objects.filter(
                year=current_year,
                quarter=current_quarter,
                unit__in=accessible_units
            ).count(),
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent_activities(self, request):
        """Get recent activities."""
        profile = self.get_user_profile()
        
        # Get accessible units
        if profile.role == 'SUPERADMIN':
            accessible_units = Unit.objects.all()
        else:
            accessible_units = Unit.objects.filter(id=profile.unit.id)
        
        # Recent activities
        recent_activities = WorkflowAudit.objects.filter(
            unit__in=accessible_units
        ).order_by('-created_at')[:10]
        
        serializer = WorkflowAuditSerializer(recent_activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get pending approvals for approvers."""
        profile = self.get_user_profile()
        
        if profile.role not in ['SUPERADMIN', 'STRATEGIC_AFFAIRS']:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get accessible units
        if profile.role == 'SUPERADMIN':
            accessible_units = Unit.objects.all()
        else:
            accessible_units = Unit.objects.filter(id=profile.unit.id)
        
        # Pending approvals
        pending_approvals = AnnualPlan.objects.filter(
            status='SUBMITTED',
            unit__in=accessible_units
        ).order_by('-submitted_at')[:5]
        
        serializer = AnnualPlanListSerializer(pending_approvals, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def performance_summary(self, request):
        """Get performance summary and analytics."""
        profile = self.get_user_profile()
        year = request.query_params.get('year', timezone.now().year)
        
        # Get accessible units
        if profile.role == 'SUPERADMIN':
            accessible_units = Unit.objects.all()
        else:
            accessible_units = Unit.objects.filter(id=profile.unit.id)
        
        # Get performance data
        annual_plans = AnnualPlan.objects.filter(year=year, unit__in=accessible_units)
        quarterly_reports = QuarterlyReport.objects.filter(year=year, unit__in=accessible_units)
        
        # Calculate statistics
        stats = {
            'year': year,
            'total_plans': annual_plans.count(),
            'approved_plans': annual_plans.filter(status='APPROVED').count(),
            'total_reports': quarterly_reports.count(),
            'approved_reports': quarterly_reports.filter(status='APPROVED').count(),
        }
        
        # Calculate completion percentages
        if stats['total_plans'] > 0:
            stats['plan_approval_rate'] = (stats['approved_plans'] / stats['total_plans']) * 100
        else:
            stats['plan_approval_rate'] = 0
        
        if stats['total_reports'] > 0:
            stats['report_approval_rate'] = (stats['approved_reports'] / stats['total_reports']) * 100
        else:
            stats['report_approval_rate'] = 0
        
        serializer = PerformanceSummarySerializer(stats)
        return Response(serializer.data)
