from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Unit, UserProfile, Indicator, AnnualPlan, AnnualPlanTarget,
    QuarterlyReport, QuarterlyIndicatorEntry, ImportBatch, WorkflowAudit
)

# Register your models here.

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'parent', 'children_count', 'users_count']
    list_filter = ['type', 'parent']
    search_fields = ['name']
    ordering = ['type', 'name']
    raw_id_fields = ['parent']
    
    def children_count(self, obj):
        return obj.children.count()
    children_count.short_description = 'Children'
    
    def users_count(self, obj):
        return obj.users.count()
    users_count.short_description = 'Users'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'unit']
    list_filter = ['role', 'unit__type']
    search_fields = ['user__username', 'user__email', 'unit__name']
    raw_id_fields = ['user', 'unit']

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'owner_unit', 'unit_of_measure', 'active']
    list_filter = ['owner_unit', 'active']
    search_fields = ['code', 'name', 'description']
    ordering = ['owner_unit__name', 'code']

@admin.register(AnnualPlan)
class AnnualPlanAdmin(admin.ModelAdmin):
    list_display = ['year', 'unit', 'status', 'created_by', 'submitted_at', 'approved_by', 'approved_at', 'targets_count', 'status_badge']
    list_filter = ['year', 'status', 'unit__type', 'submitted_at', 'approved_at']
    search_fields = ['unit__name', 'created_by__username']
    raw_id_fields = ['created_by', 'approved_by']
    readonly_fields = ['submitted_at', 'approved_at']
    date_hierarchy = 'submitted_at'
    actions = ['approve_plans', 'reject_plans']
    
    def targets_count(self, obj):
        return obj.targets.count()
    targets_count.short_description = 'Targets'
    
    def status_badge(self, obj):
        colors = {
            'DRAFT': 'orange',
            'SUBMITTED': 'blue',
            'APPROVED': 'green',
            'REJECTED': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def approve_plans(self, request, queryset):
        updated = queryset.filter(status='SUBMITTED').update(
            status='APPROVED',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} plans approved successfully.')
    approve_plans.short_description = 'Approve selected plans'
    
    def reject_plans(self, request, queryset):
        updated = queryset.filter(status='SUBMITTED').update(status='REJECTED')
        self.message_user(request, f'{updated} plans rejected.')
    reject_plans.short_description = 'Reject selected plans'

@admin.register(AnnualPlanTarget)
class AnnualPlanTargetAdmin(admin.ModelAdmin):
    list_display = ['plan', 'indicator', 'target_value', 'baseline_value']
    list_filter = ['plan__year', 'plan__unit', 'indicator__owner_unit']
    search_fields = ['indicator__code', 'indicator__name']
    raw_id_fields = ['plan', 'indicator']

@admin.register(QuarterlyReport)
class QuarterlyReportAdmin(admin.ModelAdmin):
    list_display = ['year', 'quarter', 'unit', 'status', 'created_by', 'submitted_at', 'approved_by', 'approved_at', 'entries_count', 'status_badge']
    list_filter = ['year', 'quarter', 'status', 'unit__type', 'submitted_at', 'approved_at']
    search_fields = ['unit__name', 'created_by__username']
    raw_id_fields = ['created_by', 'approved_by']
    readonly_fields = ['submitted_at', 'approved_at']
    date_hierarchy = 'submitted_at'
    actions = ['approve_reports', 'reject_reports']
    
    def entries_count(self, obj):
        return obj.entries.count()
    entries_count.short_description = 'Entries'
    
    def status_badge(self, obj):
        colors = {
            'DRAFT': 'orange',
            'SUBMITTED': 'blue',
            'APPROVED': 'green',
            'REJECTED': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def approve_reports(self, request, queryset):
        updated = queryset.filter(status='SUBMITTED').update(
            status='APPROVED',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} reports approved successfully.')
    approve_reports.short_description = 'Approve selected reports'
    
    def reject_reports(self, request, queryset):
        updated = queryset.filter(status='SUBMITTED').update(status='REJECTED')
        self.message_user(request, f'{updated} reports rejected.')
    reject_reports.short_description = 'Reject selected reports'

@admin.register(QuarterlyIndicatorEntry)
class QuarterlyIndicatorEntryAdmin(admin.ModelAdmin):
    list_display = ['report', 'indicator', 'achieved_value', 'updated_by', 'updated_at']
    list_filter = ['report__year', 'report__quarter', 'report__unit', 'indicator__owner_unit']
    search_fields = ['indicator__code', 'indicator__name']
    raw_id_fields = ['report', 'indicator', 'updated_by']

@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ['source', 'unit', 'year', 'quarter', 'uploaded_by', 'uploaded_at', 'records_inserted', 'records_updated']
    list_filter = ['source', 'year', 'quarter', 'unit__type', 'uploaded_at']
    search_fields = ['unit__name', 'uploaded_by__username']
    raw_id_fields = ['unit', 'uploaded_by']
    readonly_fields = ['uploaded_at', 'records_inserted', 'records_updated']

@admin.register(WorkflowAudit)
class WorkflowAuditAdmin(admin.ModelAdmin):
    list_display = ['actor', 'unit', 'action', 'context_plan', 'context_report', 'created_at', 'action_badge']
    list_filter = ['action', 'unit__type', 'created_at']
    search_fields = ['actor__username', 'unit__name', 'message']
    raw_id_fields = ['actor', 'unit', 'context_plan', 'context_report']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def action_badge(self, obj):
        colors = {
            'CREATE': 'green',
            'SUBMIT': 'blue',
            'APPROVE': 'green',
            'REJECT': 'red',
            'IMPORT': 'purple',
            'UPDATE': 'orange'
        }
        color = colors.get(obj.action, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'

# Inline Admin Classes for better UX
class AnnualPlanTargetInline(admin.TabularInline):
    model = AnnualPlanTarget
    extra = 0
    fields = ['indicator', 'target_value', 'baseline_value', 'remarks']

class QuarterlyIndicatorEntryInline(admin.TabularInline):
    model = QuarterlyIndicatorEntry
    extra = 0
    fields = ['indicator', 'achieved_value', 'remarks', 'evidence_file', 'updated_by', 'updated_at']
    readonly_fields = ['updated_by', 'updated_at']

# Update existing admin classes to include inlines
class AnnualPlanAdminWithInlines(AnnualPlanAdmin):
    inlines = [AnnualPlanTargetInline]

class QuarterlyReportAdminWithInlines(QuarterlyReportAdmin):
    inlines = [QuarterlyIndicatorEntryInline]

# Re-register with inlines
admin.site.unregister(AnnualPlan)
admin.site.unregister(QuarterlyReport)
admin.site.register(AnnualPlan, AnnualPlanAdminWithInlines)
admin.site.register(QuarterlyReport, QuarterlyReportAdminWithInlines)
