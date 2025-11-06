"""
Quarterly report management views for the plans app using Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from ..models import QuarterlyReport, QuarterlyIndicatorEntry, Indicator
from ..serializers import (
    QuarterlyReportSerializer, QuarterlyReportListSerializer, QuarterlyIndicatorEntrySerializer,
    QuarterlyReportValidationSerializer, BulkApproveSerializer, BulkRejectSerializer
)
from .base import BaseViewSet, can_user_access_unit, get_user_profile


class QuarterlyReportViewSet(BaseViewSet):
    """Quarterly report management API endpoints."""
    queryset = QuarterlyReport.objects.all()
    serializer_class = QuarterlyReportSerializer
    
    def get_queryset(self):
        """Filter quarterly reports based on user role, year, and quarter."""
        profile = get_user_profile(self.request.user)
        year = self.request.query_params.get('year', timezone.now().year)
        quarter = self.request.query_params.get('quarter')
        
        queryset = QuarterlyReport.objects.filter(year=year)
        
        if quarter:
            queryset = queryset.filter(quarter=quarter)
        
        if profile.role != 'SUPERADMIN':
            queryset = queryset.filter(unit=profile.unit)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set unit and created_by automatically when creating."""
        profile = get_user_profile(self.request.user)
        serializer.save(unit=profile.unit, created_by=self.request.user)
        
        # Log the action
        self.log_action(
            profile.unit,
            'CREATE',
            context_report=serializer.instance,
            message=f"Created quarterly report for Q{serializer.instance.quarter} {serializer.instance.year}"
        )
    
    def perform_update(self, serializer):
        """Log updates."""
        self.log_action(
            serializer.instance.unit,
            'UPDATE',
            context_report=serializer.instance,
            message=f"Updated quarterly report for Q{serializer.instance.quarter} {serializer.instance.year}"
        )
        serializer.save()
    
    def perform_destroy(self, instance):
        """Log deletion."""
        self.log_action(
            instance.unit,
            'DELETE',
            context_report=instance,
            message=f"Deleted quarterly report for Q{instance.quarter} {instance.year}"
        )
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit quarterly report for approval."""
        report = self.get_object()
        
        if not can_user_access_unit(request.user, report.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if report.status != 'DRAFT':
            return Response({'error': 'Only draft reports can be submitted'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not report.entries.exists():
            return Response({'error': 'Cannot submit report without entries'}, status=status.HTTP_400_BAD_REQUEST)
        
        report.status = 'SUBMITTED'
        report.submitted_at = timezone.now()
        report.save()
        
        self.log_action(
            request.user,
            report.unit,
            'SUBMIT',
            context_report=report,
            message=f"Submitted quarterly report for Q{report.quarter} {report.year}"
        )
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve quarterly report."""
        report = self.get_object()
        profile = get_user_profile(request.user)
        
        if not can_user_access_unit(request.user, report.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if profile.role not in ['SUPERADMIN', 'STRATEGIC_AFFAIRS']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        if report.status != 'SUBMITTED':
            return Response({'error': 'Only submitted reports can be approved'}, status=status.HTTP_400_BAD_REQUEST)
        
        report.status = 'APPROVED'
        report.approved_by = request.user
        report.approved_at = timezone.now()
        report.save()
        
        self.log_action(
            request.user,
            report.unit,
            'APPROVE',
            context_report=report,
            message=f"Approved quarterly report for Q{report.quarter} {report.year}"
        )
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject quarterly report."""
        report = self.get_object()
        profile = get_user_profile(request.user)
        
        if not can_user_access_unit(request.user, report.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if profile.role not in ['SUPERADMIN', 'STRATEGIC_AFFAIRS']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        if report.status != 'SUBMITTED':
            return Response({'error': 'Only submitted reports can be rejected'}, status=status.HTTP_400_BAD_REQUEST)
        
        report.status = 'REJECTED'
        report.save()
        
        self.log_action(
            request.user,
            report.unit,
            'REJECT',
            context_report=report,
            message=f"Rejected quarterly report for Q{report.quarter} {report.year}"
        )
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def entries(self, request, pk=None):
        """Get entries for a quarterly report."""
        report = self.get_object()
        
        if not can_user_access_unit(request.user, report.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        entries = report.entries.all()
        serializer = QuarterlyIndicatorEntrySerializer(entries, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_entry(self, request, pk=None):
        """Add an entry to a quarterly report."""
        report = self.get_object()
        
        if not can_user_access_unit(request.user, report.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if report.status != 'DRAFT':
            return Response({'error': 'Cannot add entries to submitted/approved reports'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = QuarterlyIndicatorEntrySerializer(data=request.data)
        if serializer.is_valid():
            # Check if indicator belongs to the same unit
            indicator_id = serializer.validated_data.get('indicator_id')
            try:
                indicator = Indicator.objects.get(id=indicator_id, owner_unit=report.unit)
                serializer.save(report=report, indicator=indicator, updated_by=request.user)
                
                self.log_action(
                    request.user,
                    report.unit,
                    'CREATE',
                    context_report=report,
                    message=f"Added entry for indicator {indicator.code}"
                )
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Indicator.DoesNotExist:
                return Response({'error': 'Invalid indicator for this unit'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def bulk_approve(self, request, pk=None):
        """Bulk approve multiple reports."""
        profile = get_user_profile(request.user)
        
        if profile.role not in ['SUPERADMIN', 'STRATEGIC_AFFAIRS']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BulkApproveSerializer(data=request.data)
        if serializer.is_valid():
            report_ids = serializer.validated_data['plan_ids']  # Reusing the same serializer
            reason = serializer.validated_data.get('reason', '')
            
            approved_count = 0
            with transaction.atomic():
                for report_id in report_ids:
                    try:
                        report = QuarterlyReport.objects.get(id=report_id)
                        if report.status == 'SUBMITTED':
                            report.status = 'APPROVED'
                            report.approved_by = request.user
                            report.approved_at = timezone.now()
                            report.save()
                            approved_count += 1
                            
                            self.log_action(
                                request.user,
                                report.unit,
                                'APPROVE',
                                context_report=report,
                                message=f"Bulk approved: {reason}"
                            )
                    except QuarterlyReport.DoesNotExist:
                        continue
            
            return Response({
                'message': f'{approved_count} reports approved successfully',
                'approved_count': approved_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuarterlyIndicatorEntryViewSet(BaseViewSet):
    """Quarterly indicator entry management API endpoints."""
    queryset = QuarterlyIndicatorEntry.objects.all()
    serializer_class = QuarterlyIndicatorEntrySerializer
    
    def get_queryset(self):
        """Filter entries based on user access."""
        profile = get_user_profile(self.request.user)
        report_id = self.request.query_params.get('report_id')
        
        if report_id:
            try:
                report = QuarterlyReport.objects.get(id=report_id)
                if can_user_access_unit(self.request.user, report.unit):
                    return QuarterlyIndicatorEntry.objects.filter(report=report)
            except QuarterlyReport.DoesNotExist:
                pass
        
        # Fallback to user's accessible reports
        if profile.role == 'SUPERADMIN':
            return QuarterlyIndicatorEntry.objects.all()
        else:
            return QuarterlyIndicatorEntry.objects.filter(report__unit=profile.unit)
    
    def perform_create(self, serializer):
        """Create entry with validation."""
        report_id = self.request.data.get('report_id')
        if not report_id:
            return Response({'error': 'report_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            report = QuarterlyReport.objects.get(id=report_id)
            if not can_user_access_unit(self.request.user, report.unit):
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
            if report.status != 'DRAFT':
                return Response({'error': 'Cannot add entries to submitted/approved reports'}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save(report=report, updated_by=self.request.user)
            
            self.log_action(
                self.request.user,
                report.unit,
                'CREATE',
                context_report=report,
                message=f"Added entry for indicator {serializer.instance.indicator.code}"
            )
            
        except QuarterlyReport.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def perform_update(self, serializer):
        """Update entry with validation."""
        entry = self.get_object()
        report = entry.report
        
        if not can_user_access_unit(self.request.user, report.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if report.status != 'DRAFT':
            return Response({'error': 'Cannot modify entries in submitted/approved reports'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save(updated_by=self.request.user)
        
        self.log_action(
            self.request.user,
            report.unit,
            'UPDATE',
            context_report=report,
            message=f"Updated entry for indicator {entry.indicator.code}"
        )
    
    def perform_destroy(self, instance):
        """Delete entry with validation."""
        report = instance.report
        
        if not can_user_access_unit(self.request.user, report.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if report.status != 'DRAFT':
            return Response({'error': 'Cannot delete entries from submitted/approved reports'}, status=status.HTTP_400_BAD_REQUEST)
        
        self.log_action(
            self.request.user,
            report.unit,
            'DELETE',
            context_report=report,
            message=f"Deleted entry for indicator {instance.indicator.code}"
        )
        
        instance.delete()