"""
API views for the plans app.
"""
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from ..models import Unit, Indicator, AnnualPlan, QuarterlyIndicatorEntry
from .base import can_user_access_unit, get_user_profile


@login_required
def get_indicators_for_unit(request, unit_id):
    """Get indicators for a specific unit (AJAX endpoint)."""
    try:
        unit = get_object_or_404(Unit, id=unit_id)
        if not can_user_access_unit(request.user, unit):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        indicators = Indicator.objects.filter(owner_unit=unit, active=True).values('id', 'code', 'name')
        return JsonResponse({'indicators': list(indicators)})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_annual_plan_progress(request, plan_id):
    """Get progress statistics for an annual plan (AJAX endpoint)."""
    try:
        plan = get_object_or_404(AnnualPlan, id=plan_id)
        if not can_user_access_unit(request.user, plan.unit):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Calculate progress statistics
        total_targets = plan.targets.count()
        completed_entries = QuarterlyIndicatorEntry.objects.filter(
            report__unit=plan.unit,
            report__year=plan.year
        ).count()
        
        progress = {
            'total_targets': total_targets,
            'completed_entries': completed_entries,
            'completion_percentage': (completed_entries / total_targets * 100) if total_targets > 0 else 0
        }
        
        return JsonResponse(progress)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_unit_statistics(request, unit_id):
    """Get statistics for a specific unit (AJAX endpoint)."""
    try:
        unit = get_object_or_404(Unit, id=unit_id)
        if not can_user_access_unit(request.user, unit):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
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
        
        return JsonResponse(stats)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_quarterly_progress(request, report_id):
    """Get progress statistics for a quarterly report (AJAX endpoint)."""
    try:
        from ..models import QuarterlyReport
        report = get_object_or_404(QuarterlyReport, id=report_id)
        if not can_user_access_unit(request.user, report.unit):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get related annual plan for comparison
        try:
            annual_plan = AnnualPlan.objects.get(
                year=report.year,
                unit=report.unit,
                status='APPROVED'
            )
            total_targets = annual_plan.targets.count()
        except AnnualPlan.DoesNotExist:
            total_targets = 0
        
        completed_entries = report.entries.count()
        
        progress = {
            'total_targets': total_targets,
            'completed_entries': completed_entries,
            'completion_percentage': (completed_entries / total_targets * 100) if total_targets > 0 else 0,
            'is_within_entry_window': report.is_within_entry_window(),
        }
        
        return JsonResponse(progress)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def validate_indicator_code(request):
    """Validate indicator code uniqueness within unit (AJAX endpoint)."""
    try:
        unit_id = request.GET.get('unit_id')
        code = request.GET.get('code')
        indicator_id = request.GET.get('indicator_id')  # For updates
        
        if not unit_id or not code:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        unit = get_object_or_404(Unit, id=unit_id)
        if not can_user_access_unit(request.user, unit):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Check if code exists for this unit
        queryset = Indicator.objects.filter(code=code, owner_unit=unit)
        
        # Exclude current indicator if updating
        if indicator_id:
            queryset = queryset.exclude(id=indicator_id)
        
        exists = queryset.exists()
        
        return JsonResponse({
            'exists': exists,
            'valid': not exists,
            'message': 'Code already exists for this unit' if exists else 'Code is available'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_dashboard_data(request):
    """Get dashboard data (AJAX endpoint)."""
    try:
        profile = get_user_profile(request.user)
        if not profile:
            return JsonResponse({'error': 'User profile not found'}, status=403)
        
        current_year = timezone.now().year
        current_quarter = ((timezone.now().month - 1) // 3) + 1
        
        # Get accessible units
        if profile.role == 'SUPERADMIN':
            accessible_units = Unit.objects.all()
        else:
            accessible_units = Unit.objects.filter(id=profile.unit.id)
        
        # Calculate statistics
        stats = {
            'total_units': accessible_units.count(),
            'total_indicators': Indicator.objects.filter(owner_unit__in=accessible_units).count(),
            'annual_plans_current': AnnualPlan.objects.filter(
                year=current_year,
                unit__in=accessible_units
            ).count(),
            'quarterly_reports_current': QuarterlyIndicatorEntry.objects.filter(
                report__year=current_year,
                report__quarter=current_quarter,
                report__unit__in=accessible_units
            ).count(),
        }
        
        return JsonResponse(stats)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_recent_activities(request):
    """Get recent activities (AJAX endpoint)."""
    try:
        profile = get_user_profile(request.user)
        if not profile:
            return JsonResponse({'error': 'User profile not found'}, status=403)
        
        # Get accessible units
        if profile.role == 'SUPERADMIN':
            accessible_units = Unit.objects.all()
        else:
            accessible_units = Unit.objects.filter(id=profile.unit.id)
        
        from ..models import WorkflowAudit
        activities = WorkflowAudit.objects.filter(
            unit__in=accessible_units
        ).order_by('-created_at')[:10].values(
            'id', 'action', 'message', 'created_at', 'actor__username', 'unit__name'
        )
        
        return JsonResponse({'activities': list(activities)})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
