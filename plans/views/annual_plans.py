"""
Annual plan management views for the plans app using Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from ..models import AnnualPlan, AnnualPlanTarget, Indicator
from ..serializers import (
    AnnualPlanSerializer, AnnualPlanListSerializer, AnnualPlanTargetSerializer,
    AnnualPlanValidationSerializer, BulkApproveSerializer, BulkRejectSerializer
)
from .base import BaseViewSet, can_user_access_unit, get_user_profile


class AnnualPlanViewSet(BaseViewSet):
    """Annual plan management API endpoints."""
    queryset = AnnualPlan.objects.all()
    serializer_class = AnnualPlanSerializer
    
    def get_queryset(self):
        """Filter annual plans based on user role and year."""
        profile = get_user_profile(self.request.user)
        year = self.request.query_params.get('year', timezone.now().year)
        
        queryset = AnnualPlan.objects.filter(year=year)
        
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
            context_plan=serializer.instance,
            message=f"Created annual plan for {serializer.instance.year}"
        )
    
    def perform_update(self, serializer):
        """Log updates."""
        self.log_action(
            serializer.instance.unit,
            'UPDATE',
            context_plan=serializer.instance,
            message=f"Updated annual plan for {serializer.instance.year}"
        )
        serializer.save()
    
    def perform_destroy(self, instance):
        """Log deletion."""
        self.log_action(
            instance.unit,
            'DELETE',
            context_plan=instance,
            message=f"Deleted annual plan for {instance.year}"
        )
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit annual plan for approval."""
        plan = self.get_object()
        
        if not can_user_access_unit(request.user, plan.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if plan.status != 'DRAFT':
            return Response({'error': 'Only draft plans can be submitted'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not plan.targets.exists():
            return Response({'error': 'Cannot submit plan without targets'}, status=status.HTTP_400_BAD_REQUEST)
        
        plan.status = 'SUBMITTED'
        plan.submitted_at = timezone.now()
        plan.save()
        
        self.log_action(
            plan.unit,
            'SUBMIT',
            context_plan=plan,
            message=f"Submitted annual plan for {plan.year}"
        )
        
        serializer = self.get_serializer(plan)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve annual plan."""
        plan = self.get_object()
        profile = get_user_profile(request.user)
        
        if not can_user_access_unit(request.user, plan.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if profile.role not in ['SUPERADMIN', 'STRATEGIC_AFFAIRS']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        if plan.status != 'SUBMITTED':
            return Response({'error': 'Only submitted plans can be approved'}, status=status.HTTP_400_BAD_REQUEST)
        
        plan.status = 'APPROVED'
        plan.approved_by = request.user
        plan.approved_at = timezone.now()
        plan.save()
        
        self.log_action(
            plan.unit,
            'APPROVE',
            context_plan=plan,
            message=f"Approved annual plan for {plan.year}"
        )
        
        serializer = self.get_serializer(plan)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject annual plan."""
        plan = self.get_object()
        profile = get_user_profile(request.user)
        
        if not can_user_access_unit(request.user, plan.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if profile.role not in ['SUPERADMIN', 'STRATEGIC_AFFAIRS']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        if plan.status != 'SUBMITTED':
            return Response({'error': 'Only submitted plans can be rejected'}, status=status.HTTP_400_BAD_REQUEST)
        
        plan.status = 'REJECTED'
        plan.save()
        
        self.log_action(
            plan.unit,
            'REJECT',
            context_plan=plan,
            message=f"Rejected annual plan for {plan.year}"
        )
        
        serializer = self.get_serializer(plan)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def targets(self, request, pk=None):
        """Get targets for an annual plan."""
        plan = self.get_object()
        
        if not can_user_access_unit(request.user, plan.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        targets = plan.targets.all()
        serializer = AnnualPlanTargetSerializer(targets, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_target(self, request, pk=None):
        """Add a target to an annual plan."""
        plan = self.get_object()
        
        if not can_user_access_unit(request.user, plan.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if plan.status != 'DRAFT':
            return Response({'error': 'Cannot add targets to submitted/approved plans'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AnnualPlanTargetSerializer(data=request.data)
        if serializer.is_valid():
            # Check if indicator belongs to the same unit
            indicator_id = serializer.validated_data.get('indicator_id')
            try:
                indicator = Indicator.objects.get(id=indicator_id, owner_unit=plan.unit)
                serializer.save(plan=plan, indicator=indicator)
                
                self.log_action(
                    plan.unit,
                    'CREATE',
                    context_plan=plan,
                    message=f"Added target for indicator {indicator.code}"
                )
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Indicator.DoesNotExist:
                return Response({'error': 'Invalid indicator for this unit'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def bulk_approve(self, request, pk=None):
        """Bulk approve multiple plans."""
        profile = get_user_profile(request.user)
        
        if profile.role not in ['SUPERADMIN', 'STRATEGIC_AFFAIRS']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BulkApproveSerializer(data=request.data)
        if serializer.is_valid():
            plan_ids = serializer.validated_data['plan_ids']
            reason = serializer.validated_data.get('reason', '')
            
            approved_count = 0
            with transaction.atomic():
                for plan_id in plan_ids:
                    try:
                        plan = AnnualPlan.objects.get(id=plan_id)
                        if plan.status == 'SUBMITTED':
                            plan.status = 'APPROVED'
                            plan.approved_by = request.user
                            plan.approved_at = timezone.now()
                            plan.save()
                            approved_count += 1
                            
                            self.log_action(
                                plan.unit,
                                'APPROVE',
                                context_plan=plan,
                                message=f"Bulk approved: {reason}"
                            )
                    except AnnualPlan.DoesNotExist:
                        continue
            
            return Response({
                'message': f'{approved_count} plans approved successfully',
                'approved_count': approved_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def bulk_reject(self, request, pk=None):
        """Bulk reject multiple plans."""
        profile = get_user_profile(request.user)
        
        if profile.role not in ['SUPERADMIN', 'STRATEGIC_AFFAIRS']:
            return Response({'error': 'Insufficient permissions'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BulkRejectSerializer(data=request.data)
        if serializer.is_valid():
            plan_ids = serializer.validated_data['plan_ids']
            reason = serializer.validated_data['reason']
            
            rejected_count = 0
            with transaction.atomic():
                for plan_id in plan_ids:
                    try:
                        plan = AnnualPlan.objects.get(id=plan_id)
                        if plan.status == 'SUBMITTED':
                            plan.status = 'REJECTED'
                            plan.save()
                            rejected_count += 1
                            
                            self.log_action(
                                plan.unit,
                                'REJECT',
                                context_plan=plan,
                                message=f"Bulk rejected: {reason}"
                            )
                    except AnnualPlan.DoesNotExist:
                        continue
            
            return Response({
                'message': f'{rejected_count} plans rejected successfully',
                'rejected_count': rejected_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnnualPlanTargetViewSet(BaseViewSet):
    """Annual plan target management API endpoints."""
    queryset = AnnualPlanTarget.objects.all()
    serializer_class = AnnualPlanTargetSerializer
    
    def get_queryset(self):
        """Filter targets based on user access."""
        profile = get_user_profile(self.request.user)
        plan_id = self.request.query_params.get('plan_id')
        
        if plan_id:
            try:
                plan = AnnualPlan.objects.get(id=plan_id)
                if can_user_access_unit(self.request.user, plan.unit):
                    return AnnualPlanTarget.objects.filter(plan=plan)
            except AnnualPlan.DoesNotExist:
                pass
        
        # Fallback to user's accessible plans
        if profile.role == 'SUPERADMIN':
            return AnnualPlanTarget.objects.all()
        else:
            return AnnualPlanTarget.objects.filter(plan__unit=profile.unit)
    
    def perform_create(self, serializer):
        """Create target with validation."""
        plan_id = self.request.data.get('plan_id')
        if not plan_id:
            return Response({'error': 'plan_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = AnnualPlan.objects.get(id=plan_id)
            if not can_user_access_unit(self.request.user, plan.unit):
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
            if plan.status != 'DRAFT':
                return Response({'error': 'Cannot add targets to submitted/approved plans'}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save(plan=plan)
            
            self.log_action(
                plan.unit,
                'CREATE',
                context_plan=plan,
                message=f"Added target for indicator {serializer.instance.indicator.code}"
            )
            
        except AnnualPlan.DoesNotExist:
            return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def perform_update(self, serializer):
        """Update target with validation."""
        target = self.get_object()
        plan = target.plan
        
        if not can_user_access_unit(self.request.user, plan.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if plan.status != 'DRAFT':
            return Response({'error': 'Cannot modify targets in submitted/approved plans'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        
        self.log_action(
            plan.unit,
            'UPDATE',
            context_plan=plan,
            message=f"Updated target for indicator {target.indicator.code}"
        )
    
    def perform_destroy(self, instance):
        """Delete target with validation."""
        plan = instance.plan
        
        if not can_user_access_unit(self.request.user, plan.unit):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if plan.status != 'DRAFT':
            return Response({'error': 'Cannot delete targets from submitted/approved plans'}, status=status.HTTP_400_BAD_REQUEST)
        
        self.log_action(
            plan.unit,
            'DELETE',
            context_plan=plan,
            message=f"Deleted target for indicator {instance.indicator.code}"
        )
        
        instance.delete()