from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Unit(models.Model):
    """Organizational units in the ministry hierarchy."""
    TYPE_CHOICES = [
        ('STRATEGIC', 'Strategic Affairs Office'),
        ('STATE_MINISTER', 'State Minister Office'),
        ('ADVISOR', 'State Minister Advisor Office'),
    ]
    name = models.CharField(max_length=200, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')

    class Meta:
        ordering = ['type', 'name']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Attach roles and unit to users."""
    ROLE_CHOICES = [
        ('SUPERADMIN', 'Super Admin'),
        ('STRATEGIC_AFFAIRS', 'Strategic Affairs'),
        ('STATE_MINISTER', 'State Minister'),
        ('ADVISOR', 'State Minister Advisor'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='users')

    def __str__(self):
        return f'{self.user.username} ({self.role})'
    
class Indicator(models.Model):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='indicators')
    unit_of_measure = models.CharField(max_length=50, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = [('owner_unit', 'code')]
        ordering = ['owner_unit__name', 'code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class AnnualPlan(models.Model):
    """Annual plan per State Minister Office or Advisor Office with approval flow."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    year = models.PositiveIntegerField()
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='annual_plans')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='plans_created')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='plans_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    # Optional explicit entry window override; if null, default rule is 30 days from Jan 1
    entry_window_start = models.DateTimeField(null=True, blank=True)
    entry_window_end = models.DateTimeField(null=True, blank=True)
    class Meta:
        unique_together = [('year', 'unit')]
        ordering = ['-year', 'unit__name']

    def __str__(self):
        return f'{self.unit.name} - Annual Plan {self.year}'

    def default_entry_window(self):
        start = timezone.datetime(self.year, 1, 1, tzinfo=timezone.get_current_timezone())
        end = start + timezone.timedelta(days=30)
        return start, end

    def is_within_entry_window(self, when=None):
        when = when or timezone.now()
        start = self.entry_window_start
        end = self.entry_window_end
        if not start or not end:
            start, end = self.default_entry_window()
        return start <= when <= end


class AnnualPlanTarget(models.Model):
    """Target per indicator inside an annual plan."""
    plan = models.ForeignKey(AnnualPlan, on_delete=models.CASCADE, related_name='targets')
    indicator = models.ForeignKey(Indicator, on_delete=models.PROTECT, related_name='annual_targets')
    target_value = models.DecimalField(max_digits=20, decimal_places=4)
    baseline_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = [('plan', 'indicator')]
        ordering = ['indicator__code']

class QuarterlyReport(models.Model):
    """Quarterly performance report with approval flow and entry window."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    QUARTER_CHOICES = [(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')]

    year = models.PositiveIntegerField()
    quarter = models.IntegerField(choices=QUARTER_CHOICES)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='quarterly_reports')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='qreports_created')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='qreports_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    # Optional explicit entry window; if null, default rule is 15 days after quarter end
    entry_window_start = models.DateTimeField(null=True, blank=True)
    entry_window_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('year', 'quarter', 'unit')]
        ordering = ['-year', '-quarter', 'unit__name']

    def __str__(self):
        return f'{self.unit.name} - Q{self.quarter} {self.year}'

    def quarter_date_range(self):
        tz = timezone.get_current_timezone()
        if self.quarter == 1:
            start = timezone.datetime(self.year, 1, 1, tzinfo=tz)
            end = timezone.datetime(self.year, 3, 31, 23, 59, 59, tzinfo=tz)
        elif self.quarter == 2:
            start = timezone.datetime(self.year, 4, 1, tzinfo=tz)
            end = timezone.datetime(self.year, 6, 30, 23, 59, 59, tzinfo=tz)
        elif self.quarter == 3:
            start = timezone.datetime(self.year, 7, 1, tzinfo=tz)
            end = timezone.datetime(self.year, 9, 30, 23, 59, 59, tzinfo=tz)
        else:
            start = timezone.datetime(self.year, 10, 1, tzinfo=tz)
            end = timezone.datetime(self.year, 12, 31, 23, 59, 59, tzinfo=tz)
        return start, end

    def default_entry_window(self):
        _, qend = self.quarter_date_range()
        start = qend  # allow starting at quarter end
        end = qend + timezone.timedelta(days=15)
        return start, end

    def is_within_entry_window(self, when=None):
        when = when or timezone.now()
        start = self.entry_window_start
        end = self.entry_window_end
        if not start or not end:
            start, end = self.default_entry_window()
        return start <= when <= end


class QuarterlyIndicatorEntry(models.Model):
    """Achieved values per indicator in a quarterly report."""
    report = models.ForeignKey(QuarterlyReport, on_delete=models.CASCADE, related_name='entries')
    indicator = models.ForeignKey(Indicator, on_delete=models.PROTECT, related_name='quarterly_entries')
    achieved_value = models.DecimalField(max_digits=20, decimal_places=4)
    remarks = models.TextField(blank=True, null=True)
    evidence_file = models.FileField(upload_to='evidence/', null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='qentries_updated')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('report', 'indicator')]
        ordering = ['indicator__code']
class ImportBatch(models.Model):
    """Track Excel uploads for auditing and upsert behavior."""
    SOURCE_CHOICES = [
        ('ANNUAL', 'Annual Plan'),
        ('QUARTERLY', 'Quarterly Report'),
    ]
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    file = models.FileField(upload_to='imports/')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='imports')
    year = models.PositiveIntegerField()
    quarter = models.IntegerField(null=True, blank=True)  # only for QUARTERLY
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='imports_uploaded')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    records_inserted = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)


class WorkflowAudit(models.Model):
    """Audit trail for submissions and approvals."""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('SUBMIT', 'Submit'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('IMPORT', 'Import'),
        ('UPDATE', 'Update'),
    ]
    actor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='wf_actions')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='wf_logs')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    context_plan = models.ForeignKey(AnnualPlan, null=True, blank=True, on_delete=models.CASCADE, related_name='audit_logs')
    context_report = models.ForeignKey(QuarterlyReport, null=True, blank=True, on_delete=models.CASCADE, related_name='audit_logs')
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
