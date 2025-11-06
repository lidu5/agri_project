"""
Base views and utility functions for the plans app using Django REST Framework.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from ..models import UserProfile, WorkflowAudit


def get_user_profile(user):
    """Get user profile or create one if it doesn't exist."""
    if user.is_anonymous:
        return None
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def can_user_access_unit(user, unit):
    """Check if user can access a specific unit."""
    profile = get_user_profile(user)
    if not profile:
        return False
    
    # Super admin can access all units
    if profile.role == 'SUPERADMIN':
        return True
    
    # Users can only access their own unit
    return profile.unit == unit


def log_workflow_action(user, unit, action, context_plan=None, context_report=None, message=""):
    """Log workflow actions for audit trail."""
    WorkflowAudit.objects.create(
        actor=user,
        unit=unit,
        action=action,
        context_plan=context_plan,
        context_report=context_report,
        message=message
    )


class BaseViewSet(viewsets.ModelViewSet):
    """Base ViewSet with common functionality for all views."""
    permission_classes = [IsAuthenticated]
    
    def dispatch(self, request, *args, **kwargs):
        """Check user profile exists before processing view."""
        return super().dispatch(request, *args, **kwargs)
        # if not get_user_profile(request.user):
        #     return Response(
        #         {'error': 'User profile not found. Please contact administrator.'},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        # return super().dispatch(request, *args, **kwargs)
    
    def get_user_profile(self):
        """Get the current user's profile."""
        profile = get_user_profile(self.request.user)
        if not profile:
            # Return a more helpful error message
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "User profile not found. Please contact administrator to set up your profile."
            )
        return profile
    
    def can_access_unit(self, unit):
        """Check if current user can access a unit."""
        return can_user_access_unit(self.request.user, unit)
    
    def log_action(self, unit, action, context_plan=None, context_report=None, message=""):
        """Log a workflow action."""
        log_workflow_action(
            self.request.user,
            unit,
            action,
            context_plan,
            context_report,
            message
        )
