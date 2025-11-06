"""
Unit management views for the plans app using Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import PermissionDenied

from ..models import Unit, Indicator, AnnualPlan, QuarterlyReport
from ..serializers import UnitSerializer, IndicatorNestedSerializer, AnnualPlanListSerializer, QuarterlyReportListSerializer
from .base import BaseViewSet, can_user_access_unit, get_user_profile


class UnitViewSet(BaseViewSet):
    """Unit management API endpoints."""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    
    def get_queryset(self):
        """Filter units based on user role."""
        profile = get_user_profile(self.request.user)
        if profile.role == 'SUPERADMIN':
            return Unit.objects.all()
        else:
            return Unit.objects.filter(id=profile.unit.id)
    
    def retrieve(self, request, *args, **kwargs):
        """Get unit details with related data."""
        unit = self.get_object()
        
        if not can_user_access_unit(request.user, unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get related data
        indicators = unit.indicators.filter(active=True)
        annual_plans = unit.annual_plans.order_by('-year')[:5]
        quarterly_reports = unit.quarterly_reports.order_by('-year', '-quarter')[:5]
        
        # Serialize the main unit
        unit_serializer = self.get_serializer(unit)
        
        # Serialize related data
        indicators_data = IndicatorNestedSerializer(indicators, many=True).data
        annual_plans_data = AnnualPlanListSerializer(annual_plans, many=True).data
        quarterly_reports_data = QuarterlyReportListSerializer(quarterly_reports, many=True).data
        
        response_data = unit_serializer.data
        response_data.update({
            'indicators': indicators_data,
            'annual_plans': annual_plans_data,
            'quarterly_reports': quarterly_reports_data,
        })
        
        return Response(response_data)
    
    @action(detail=True, methods=['get'])
    def indicators(self, request, pk=None):
        """Get indicators for a specific unit."""
        unit = self.get_object()
        
        if not can_user_access_unit(request.user, unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        indicators = unit.indicators.filter(active=True)
        serializer = IndicatorNestedSerializer(indicators, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def annual_plans(self, request, pk=None):
        """Get annual plans for a specific unit."""
        unit = self.get_object()
        
        if not can_user_access_unit(request.user, unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        year = request.query_params.get('year')
        queryset = unit.annual_plans.all()
        
        if year:
            queryset = queryset.filter(year=year)
        
        queryset = queryset.order_by('-year')[:10]  # Limit to 10 most recent
        serializer = AnnualPlanListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def quarterly_reports(self, request, pk=None):
        """Get quarterly reports for a specific unit."""
        unit = self.get_object()
        
        if not can_user_access_unit(request.user, unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        year = request.query_params.get('year')
        quarter = request.query_params.get('quarter')
        
        queryset = unit.quarterly_reports.all()
        
        if year:
            queryset = queryset.filter(year=year)
        if quarter:
            queryset = queryset.filter(quarter=quarter)
        
        queryset = queryset.order_by('-year', '-quarter')[:10]  # Limit to 10 most recent
        serializer = QuarterlyReportListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a specific unit."""
        unit = self.get_object()
        
        if not can_user_access_unit(request.user, unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        from django.utils import timezone
        current_year = timezone.now().year
        
        stats = {
            'indicators_count': unit.indicators.filter(active=True).count(),
            'annual_plans_count': unit.annual_plans.filter(year=current_year).count(),
            'quarterly_reports_count': unit.quarterly_reports.filter(year=current_year).count(),
            'pending_approvals': unit.annual_plans.filter(
                year=current_year,
                status='SUBMITTED'
            ).count(),
        }
        
        return Response(stats)
