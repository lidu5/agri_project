from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Unit, UserProfile, Indicator, AnnualPlan, AnnualPlanTarget,
    QuarterlyReport, QuarterlyIndicatorEntry, ImportBatch, WorkflowAudit
)


# =============================================================================
# BASE SERIALIZERS
# =============================================================================

class UserSerializer(serializers.ModelSerializer):
    """User serializer with basic information."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active']
        read_only_fields = ['id']


class UnitSerializer(serializers.ModelSerializer):
    """Unit serializer with hierarchy support."""
    children_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Unit
        fields = [
            'id', 'name', 'type', 'parent', 'parent_name',
            'children_count', 'users_count'
        ]
        read_only_fields = ['id']
    
    def get_children_count(self, obj):
        return obj.children.count()
    
    def get_users_count(self, obj):
        return obj.users.count()


class UnitNestedSerializer(serializers.ModelSerializer):
    """Simplified unit serializer for nested relationships."""
    class Meta:
        model = Unit
        fields = ['id', 'name', 'type']


# =============================================================================
# USER PROFILE SERIALIZERS
# =============================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer with user and unit details."""
    user = UserSerializer(read_only=True)
    unit = UnitNestedSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    unit_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'user_id', 'role', 'unit', 'unit_id'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        user_id = validated_data.pop('user_id')
        unit_id = validated_data.pop('unit_id')
        
        user = User.objects.get(id=user_id)
        unit = Unit.objects.get(id=unit_id)
        
        return UserProfile.objects.create(
            user=user,
            unit=unit,
            **validated_data
        )
    
    def update(self, instance, validated_data):
        if 'user_id' in validated_data:
            user_id = validated_data.pop('user_id')
            instance.user = User.objects.get(id=user_id)
        
        if 'unit_id' in validated_data:
            unit_id = validated_data.pop('unit_id')
            instance.unit = Unit.objects.get(id=unit_id)
        
        return super().update(instance, validated_data)


# =============================================================================
# INDICATOR SERIALIZERS
# =============================================================================

class IndicatorSerializer(serializers.ModelSerializer):
    """Indicator serializer with unit information."""
    owner_unit = UnitNestedSerializer(read_only=True)
    owner_unit_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Indicator
        fields = [
            'id', 'code', 'name', 'description', 'owner_unit', 'owner_unit_id',
            'unit_of_measure', 'active'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        owner_unit_id = validated_data.pop('owner_unit_id')
        owner_unit = Unit.objects.get(id=owner_unit_id)
        
        return Indicator.objects.create(
            owner_unit=owner_unit,
            **validated_data
        )
    
    def update(self, instance, validated_data):
        if 'owner_unit_id' in validated_data:
            owner_unit_id = validated_data.pop('owner_unit_id')
            instance.owner_unit = Unit.objects.get(id=owner_unit_id)
        
        return super().update(instance, validated_data)


class IndicatorNestedSerializer(serializers.ModelSerializer):
    """Simplified indicator serializer for nested relationships."""
    class Meta:
        model = Indicator
        fields = ['id', 'code', 'name', 'unit_of_measure']


# =============================================================================
# ANNUAL PLAN SERIALIZERS
# =============================================================================

class AnnualPlanTargetSerializer(serializers.ModelSerializer):
    """Annual plan target serializer."""
    indicator = IndicatorNestedSerializer(read_only=True)
    indicator_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = AnnualPlanTarget
        fields = [
            'id', 'indicator', 'indicator_id', 'target_value',
            'baseline_value', 'remarks'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        indicator_id = validated_data.pop('indicator_id')
        indicator = Indicator.objects.get(id=indicator_id)
        
        return AnnualPlanTarget.objects.create(
            indicator=indicator,
            **validated_data
        )
    
    def update(self, instance, validated_data):
        if 'indicator_id' in validated_data:
            indicator_id = validated_data.pop('indicator_id')
            instance.indicator = Indicator.objects.get(id=indicator_id)
        
        return super().update(instance, validated_data)


class AnnualPlanSerializer(serializers.ModelSerializer):
    """Annual plan serializer with targets and workflow information."""
    unit = UnitNestedSerializer(read_only=True)
    unit_id = serializers.IntegerField(write_only=True)
    created_by = UserSerializer(read_only=True)
    created_by_id = serializers.IntegerField(write_only=True)
    approved_by = UserSerializer(read_only=True)
    targets = AnnualPlanTargetSerializer(many=True, read_only=True)
    targets_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_submit = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    is_within_entry_window = serializers.SerializerMethodField()
    
    class Meta:
        model = AnnualPlan
        fields = [
            'id', 'year', 'unit', 'unit_id', 'status', 'created_by', 'created_by_id',
            'submitted_at', 'approved_by', 'approved_at', 'entry_window_start',
            'entry_window_end', 'targets', 'targets_count', 'can_edit', 'can_submit',
            'can_approve', 'is_within_entry_window'
        ]
        read_only_fields = ['id', 'submitted_at', 'approved_at']
    
    def get_targets_count(self, obj):
        return obj.targets.count()
    
    def get_can_edit(self, obj):
        return obj.status in ['DRAFT'] and obj.is_within_entry_window()
    
    def get_can_submit(self, obj):
        return obj.status == 'DRAFT' and obj.targets.exists()
    
    def get_can_approve(self, obj):
        # This would need to be determined by the requesting user's role
        return obj.status == 'SUBMITTED'
    
    def get_is_within_entry_window(self, obj):
        return obj.is_within_entry_window()
    
    def create(self, validated_data):
        unit_id = validated_data.pop('unit_id')
        created_by_id = validated_data.pop('created_by_id')
        
        unit = Unit.objects.get(id=unit_id)
        created_by = User.objects.get(id=created_by_id)
        
        return AnnualPlan.objects.create(
            unit=unit,
            created_by=created_by,
            **validated_data
        )
    
    def update(self, instance, validated_data):
        if 'unit_id' in validated_data:
            unit_id = validated_data.pop('unit_id')
            instance.unit = Unit.objects.get(id=unit_id)
        
        if 'created_by_id' in validated_data:
            created_by_id = validated_data.pop('created_by_id')
            instance.created_by = User.objects.get(id=created_by_id)
        
        return super().update(instance, validated_data)


class AnnualPlanListSerializer(serializers.ModelSerializer):
    """Simplified annual plan serializer for list views."""
    unit = UnitNestedSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    targets_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AnnualPlan
        fields = [
            'id', 'year', 'unit', 'status', 'created_by',
            'submitted_at', 'approved_at', 'targets_count'
        ]
    
    def get_targets_count(self, obj):
        return obj.targets.count()


# =============================================================================
# QUARTERLY REPORT SERIALIZERS
# =============================================================================

class QuarterlyIndicatorEntrySerializer(serializers.ModelSerializer):
    """Quarterly indicator entry serializer."""
    indicator = IndicatorNestedSerializer(read_only=True)
    indicator_id = serializers.IntegerField(write_only=True)
    updated_by = UserSerializer(read_only=True)
    updated_by_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = QuarterlyIndicatorEntry
        fields = [
            'id', 'indicator', 'indicator_id', 'achieved_value',
            'remarks', 'evidence_file', 'updated_by', 'updated_by_id', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']
    
    def create(self, validated_data):
        indicator_id = validated_data.pop('indicator_id')
        updated_by_id = validated_data.pop('updated_by_id')
        
        indicator = Indicator.objects.get(id=indicator_id)
        updated_by = User.objects.get(id=updated_by_id)
        
        return QuarterlyIndicatorEntry.objects.create(
            indicator=indicator,
            updated_by=updated_by,
            **validated_data
        )
    
    def update(self, instance, validated_data):
        if 'indicator_id' in validated_data:
            indicator_id = validated_data.pop('indicator_id')
            instance.indicator = Indicator.objects.get(id=indicator_id)
        
        if 'updated_by_id' in validated_data:
            updated_by_id = validated_data.pop('updated_by_id')
            instance.updated_by = User.objects.get(id=updated_by_id)
        
        return super().update(instance, validated_data)


class QuarterlyReportSerializer(serializers.ModelSerializer):
    """Quarterly report serializer with entries and workflow information."""
    unit = UnitNestedSerializer(read_only=True)
    unit_id = serializers.IntegerField(write_only=True)
    created_by = UserSerializer(read_only=True)
    created_by_id = serializers.IntegerField(write_only=True)
    approved_by = UserSerializer(read_only=True)
    entries = QuarterlyIndicatorEntrySerializer(many=True, read_only=True)
    entries_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_submit = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    is_within_entry_window = serializers.SerializerMethodField()
    quarter_display = serializers.CharField(source='get_quarter_display', read_only=True)
    
    class Meta:
        model = QuarterlyReport
        fields = [
            'id', 'year', 'quarter', 'quarter_display', 'unit', 'unit_id', 'status',
            'created_by', 'created_by_id', 'submitted_at', 'approved_by', 'approved_at',
            'entry_window_start', 'entry_window_end', 'entries', 'entries_count',
            'can_edit', 'can_submit', 'can_approve', 'is_within_entry_window'
        ]
        read_only_fields = ['id', 'submitted_at', 'approved_at']
    
    def get_entries_count(self, obj):
        return obj.entries.count()
    
    def get_can_edit(self, obj):
        return obj.status in ['DRAFT'] and obj.is_within_entry_window()
    
    def get_can_submit(self, obj):
        return obj.status == 'DRAFT' and obj.entries.exists()
    
    def get_can_approve(self, obj):
        # This would need to be determined by the requesting user's role
        return obj.status == 'SUBMITTED'
    
    def get_is_within_entry_window(self, obj):
        return obj.is_within_entry_window()
    
    def create(self, validated_data):
        unit_id = validated_data.pop('unit_id')
        created_by_id = validated_data.pop('created_by_id')
        
        unit = Unit.objects.get(id=unit_id)
        created_by = User.objects.get(id=created_by_id)
        
        return QuarterlyReport.objects.create(
            unit=unit,
            created_by=created_by,
            **validated_data
        )
    
    def update(self, instance, validated_data):
        if 'unit_id' in validated_data:
            unit_id = validated_data.pop('unit_id')
            instance.unit = Unit.objects.get(id=unit_id)
        
        if 'created_by_id' in validated_data:
            created_by_id = validated_data.pop('created_by_id')
            instance.created_by = User.objects.get(id=created_by_id)
        
        return super().update(instance, validated_data)


class QuarterlyReportListSerializer(serializers.ModelSerializer):
    """Simplified quarterly report serializer for list views."""
    unit = UnitNestedSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    entries_count = serializers.SerializerMethodField()
    quarter_display = serializers.CharField(source='get_quarter_display', read_only=True)
    
    class Meta:
        model = QuarterlyReport
        fields = [
            'id', 'year', 'quarter', 'quarter_display', 'unit', 'status',
            'created_by', 'submitted_at', 'approved_at', 'entries_count'
        ]
    
    def get_entries_count(self, obj):
        return obj.entries.count()


# =============================================================================
# IMPORT/EXPORT SERIALIZERS
# =============================================================================

class ImportBatchSerializer(serializers.ModelSerializer):
    """Import batch serializer for tracking Excel uploads."""
    unit = UnitNestedSerializer(read_only=True)
    unit_id = serializers.IntegerField(write_only=True)
    uploaded_by = UserSerializer(read_only=True)
    uploaded_by_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ImportBatch
        fields = [
            'id', 'source', 'file', 'unit', 'unit_id', 'year', 'quarter',
            'uploaded_by', 'uploaded_by_id', 'uploaded_at', 'records_inserted',
            'records_updated', 'notes'
        ]
        read_only_fields = ['id', 'uploaded_at', 'records_inserted', 'records_updated']
    
    def create(self, validated_data):
        unit_id = validated_data.pop('unit_id')
        uploaded_by_id = validated_data.pop('uploaded_by_id')
        
        unit = Unit.objects.get(id=unit_id)
        uploaded_by = User.objects.get(id=uploaded_by_id)
        
        return ImportBatch.objects.create(
            unit=unit,
            uploaded_by=uploaded_by,
            **validated_data
        )


# =============================================================================
# AUDIT SERIALIZERS
# =============================================================================

class WorkflowAuditSerializer(serializers.ModelSerializer):
    """Workflow audit serializer for tracking actions."""
    actor = UserSerializer(read_only=True)
    unit = UnitNestedSerializer(read_only=True)
    context_plan = AnnualPlanListSerializer(read_only=True)
    context_report = QuarterlyReportListSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = WorkflowAudit
        fields = [
            'id', 'actor', 'unit', 'action', 'action_display',
            'context_plan', 'context_report', 'message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# =============================================================================
# DASHBOARD & ANALYTICS SERIALIZERS
# =============================================================================

class DashboardStatsSerializer(serializers.Serializer):
    """Dashboard statistics serializer."""
    total_units = serializers.IntegerField()
    total_indicators = serializers.IntegerField()
    annual_plans_current = serializers.IntegerField()
    quarterly_reports_current = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    recent_activities_count = serializers.IntegerField()


class PerformanceSummarySerializer(serializers.Serializer):
    """Performance summary serializer."""
    year = serializers.IntegerField()
    total_plans = serializers.IntegerField()
    approved_plans = serializers.IntegerField()
    total_reports = serializers.IntegerField()
    approved_reports = serializers.IntegerField()
    completion_percentage = serializers.FloatField()


class AnnualPlanProgressSerializer(serializers.Serializer):
    """Annual plan progress serializer."""
    plan_id = serializers.IntegerField()
    total_targets = serializers.IntegerField()
    completed_entries = serializers.IntegerField()
    completion_percentage = serializers.FloatField()


# =============================================================================
# BULK OPERATION SERIALIZERS
# =============================================================================

class BulkApproveSerializer(serializers.Serializer):
    """Serializer for bulk approval operations."""
    plan_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    reason = serializers.CharField(max_length=500, required=False)


class BulkRejectSerializer(serializers.Serializer):
    """Serializer for bulk rejection operations."""
    plan_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    reason = serializers.CharField(max_length=500, required=True)


# =============================================================================
# VALIDATION SERIALIZERS
# =============================================================================

class IndicatorValidationSerializer(serializers.Serializer):
    """Serializer for indicator validation."""
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    owner_unit_id = serializers.IntegerField()
    
    def validate_code(self, value):
        """Validate indicator code uniqueness within unit."""
        owner_unit_id = self.initial_data.get('owner_unit_id')
        if owner_unit_id:
            if Indicator.objects.filter(
                code=value,
                owner_unit_id=owner_unit_id
            ).exists():
                raise serializers.ValidationError(
                    "An indicator with this code already exists for this unit."
                )
        return value


class AnnualPlanValidationSerializer(serializers.Serializer):
    """Serializer for annual plan validation."""
    year = serializers.IntegerField()
    unit_id = serializers.IntegerField()
    
    def validate(self, data):
        """Validate annual plan uniqueness."""
        if AnnualPlan.objects.filter(
            year=data['year'],
            unit_id=data['unit_id']
        ).exists():
            raise serializers.ValidationError(
                "An annual plan already exists for this unit and year."
            )
        return data


class QuarterlyReportValidationSerializer(serializers.Serializer):
    """Serializer for quarterly report validation."""
    year = serializers.IntegerField()
    quarter = serializers.IntegerField()
    unit_id = serializers.IntegerField()
    
    def validate_quarter(self, value):
        """Validate quarter is between 1 and 4."""
        if not 1 <= value <= 4:
            raise serializers.ValidationError("Quarter must be between 1 and 4.")
        return value
    
    def validate(self, data):
        """Validate quarterly report uniqueness."""
        if QuarterlyReport.objects.filter(
            year=data['year'],
            quarter=data['quarter'],
            unit_id=data['unit_id']
        ).exists():
            raise serializers.ValidationError(
                "A quarterly report already exists for this unit, year, and quarter."
            )
        return data


# =============================================================================
# EXPORT SERIALIZERS
# =============================================================================

class AnnualPlanExportSerializer(serializers.ModelSerializer):
    """Serializer for annual plan export."""
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    targets = AnnualPlanTargetSerializer(many=True, read_only=True)
    
    class Meta:
        model = AnnualPlan
        fields = [
            'id', 'year', 'unit_name', 'status', 'submitted_at', 'approved_at', 'targets'
        ]


class QuarterlyReportExportSerializer(serializers.ModelSerializer):
    """Serializer for quarterly report export."""
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    quarter_display = serializers.CharField(source='get_quarter_display', read_only=True)
    entries = QuarterlyIndicatorEntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = QuarterlyReport
        fields = [
            'id', 'year', 'quarter', 'quarter_display', 'unit_name', 'status',
            'submitted_at', 'approved_at', 'entries'
        ]
