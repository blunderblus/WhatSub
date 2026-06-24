from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from subscriptions.models import (
    BillingPeriod, Platform, SubscriptionPlan, UserSubscription,
)

User = get_user_model()


class SignUpForm(UserCreationForm):
    nickname = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ['username', 'nickname', 'email']

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.nickname:
            user.nickname = (user.username or '')[:30] or 'User'
        if commit:
            user.save()
        return user


class PlanSelect(forms.Select):
    """Render plan metadata for platform filtering and autofill on the page."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        plan = getattr(value, 'instance', None)
        if plan:
            option['attrs']['data-platform'] = str(plan.platform_id)
            option['attrs']['data-plan-name'] = plan.plan_name
            option['attrs']['data-price'] = str(plan.price)
            option['attrs']['data-billing-period'] = plan.billing_period
        return option


class ManualSubscriptionForm(forms.ModelForm):
    """Add a subscription by picking a known platform/plan, or entering free-text."""
    platform = forms.ModelChoiceField(
        queryset=Platform.objects.order_by('name'),
        empty_label='플랫폼 선택',
    )
    plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.select_related('platform').order_by('platform__name', 'price'),
        required=False,
        empty_label='플랜 선택 (선택 사항)',
        widget=PlanSelect,
    )

    class Meta:
        model = UserSubscription
        fields = [
            'platform', 'plan', 'plan_name', 'payment_amount',
            'billing_cycle', 'payment_method', 'start_date',
            'renewal_date', 'auto_renew', 'memo',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'renewal_date': forms.DateInput(attrs={'type': 'date'}),
            'memo': forms.Textarea(attrs={'rows': 2}),
            'billing_cycle': forms.Select(choices=BillingPeriod.choices),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These can be auto-filled from the selected plan, so don't force them.
        for field in ('plan_name', 'payment_amount', 'billing_cycle', 'payment_method', 'renewal_date'):
            self.fields[field].required = False

    def clean(self):
        cleaned = super().clean()
        platform = cleaned.get('platform')
        plan = cleaned.get('plan')
        if platform and plan and plan.platform_id != platform.id:
            self.add_error('plan', '선택한 플랫폼의 플랜만 선택할 수 있습니다.')
            cleaned['plan'] = None
            plan = None

        # Auto-fill from the selected plan when fields are left blank.
        if plan:
            if not cleaned.get('plan_name'):
                cleaned['plan_name'] = plan.plan_name
            if cleaned.get('payment_amount') in (None, ''):
                cleaned['payment_amount'] = plan.price
            if not cleaned.get('billing_cycle'):
                cleaned['billing_cycle'] = plan.billing_period

        if not cleaned.get('billing_cycle'):
            cleaned['billing_cycle'] = BillingPeriod.MONTHLY
        if not cleaned.get('plan_name'):
            cleaned['plan_name'] = '미정'
        cleaned.setdefault('payment_method', '')
        if cleaned.get('payment_method') is None:
            cleaned['payment_method'] = ''

        if cleaned.get('payment_amount') in (None, ''):
            self.add_error('payment_amount', '플랜을 선택하거나 결제 금액을 입력하세요.')

        # Default renewal date to the start date when omitted.
        if not cleaned.get('renewal_date') and cleaned.get('start_date'):
            cleaned['renewal_date'] = cleaned['start_date']

        return cleaned
