"""
Audit and reporting views for the plans app using Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.core.paginator import Paginator

from ..models import WorkflowAudit, Unit, AnnualPlan, QuarterlyReport
from ..serializers import WorkflowAuditSerializer, PerformanceSummarySerializer
from .base import BaseViewSet, get_user_profile


class AuditViewSet(BaseViewSet):
    """Audit and reporting API endpoints."""
    queryset = WorkflowAudit.objects.all()
    serializer_class = WorkflowAuditSerializer
    
    def get_queryset(self):
        """Filter audit logs based on user access."""
        profile = get_user_profile(self.request.user)
        
        # Get accessible units
        if profile.role == 'SUPERADMIN':
            accessible_units = Unit.objects.all()
        else:
            accessible_units = Unit.objects.filter(id=profile.unit.id)
        
        return WorkflowAudit.objects.filter(unit__in=accessible_units).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def recent_activities(self, request):
        """Get recent activities."""
        profile = get_user_profile(request.user)
        
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
    def performance_summary(self, request):
        """Get performance summary and analytics."""
        profile = get_user_profile(request.user)
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
    
    @action(detail=False, methods=['get'])
    def unit_performance(self, request):
        """Get performance summary for a specific unit."""
        profile = get_user_profile(request.user)
        unit_id = request.query_params.get('unit_id')
        
        if not unit_id:
            return Response({'error': 'unit_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            unit = Unit.objects.get(id=unit_id)
            
            # Check access permissions
            if profile.role != 'SUPERADMIN' and profile.unit != unit:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
            year = request.query_params.get('year', timezone.now().year)
            
            # Get performance data for this unit
            annual_plans = AnnualPlan.objects.filter(year=year, unit=unit)
            quarterly_reports = QuarterlyReport.objects.filter(year=year, unit=unit)
            
            # Calculate detailed statistics
            stats = {
                'unit_name': unit.name,
                'year': year,
                'total_plans': annual_plans.count(),
                'draft_plans': annual_plans.filter(status='DRAFT').count(),
                'submitted_plans': annual_plans.filter(status='SUBMITTED').count(),
                'approved_plans': annual_plans.filter(status='APPROVED').count(),
                'rejected_plans': annual_plans.filter(status='REJECTED').count(),
                'total_reports': quarterly_reports.count(),
                'draft_reports': quarterly_reports.filter(status='DRAFT').count(),
                'submitted_reports': quarterly_reports.filter(status='SUBMITTED').count(),
                'approved_reports': quarterly_reports.filter(status='APPROVED').count(),
                'rejected_reports': quarterly_reports.filter(status='REJECTED').count(),
            }
            
            # Calculate completion rates
            if stats['total_plans'] > 0:
                stats['plan_approval_rate'] = (stats['approved_plans'] / stats['total_plans']) * 100
            else:
                stats['plan_approval_rate'] = 0
            
            if stats['total_reports'] > 0:
                stats['report_approval_rate'] = (stats['approved_reports'] / stats['total_reports']) * 100
            else:
                stats['report_approval_rate'] = 0
            
            # Get recent activities for this unit
            recent_activities = WorkflowAudit.objects.filter(
                unit=unit
            ).order_by('-created_at')[:10]
            
            recent_activities_data = WorkflowAuditSerializer(recent_activities, many=True).data
            
            return Response({
                'unit': {
                    'id': unit.id,
                    'name': unit.name,
                    'type': unit.type
                },
                'stats': stats,
                'recent_activities': recent_activities_data
            })
            
        except Unit.DoesNotExist:
            return Response({'error': 'Unit not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def export_audit_log(self, request):
        """Export audit log as CSV."""
        profile = get_user_profile(request.user)
        
        # Get accessible units
        if profile.role == 'SUPERADMIN':
            accessible_units = Unit.objects.all()
        else:
            accessible_units = Unit.objects.filter(id=profile.unit.id)
        
        # Get audit logs
        audit_logs = WorkflowAudit.objects.filter(
            unit__in=accessible_units
        ).select_related('actor', 'unit', 'context_plan', 'context_report').order_by('-created_at')
        
        # Create CSV response
        from django.http import HttpResponse
        import csv
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_log.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Actor', 'Unit', 'Action', 'Context Plan', 'Context Report', 'Message', 'Created At'
        ])
        
        for log in audit_logs:
            writer.writerow([
                log.actor.username,
                log.unit.name,
                log.get_action_display(),
                f"{log.context_plan.unit.name} - {log.context_plan.year}" if log.context_plan else '',
                f"{log.context_report.unit.name} - Q{log.context_report.quarter} {log.context_report.year}" if log.context_report else '',
                log.message or '',
                log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response