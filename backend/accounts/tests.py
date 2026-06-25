from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.google_auth import GOOGLE_AUTH_INTENT_LOGIN, social_login_matches_existing_user
from subscriptions.models import Category, Platform, SubscriptionPlan, UserSubscription


class ManualSubscriptionFormTest(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Streaming')
        self.netflix = Platform.objects.create(name='Netflix', category=category)
        self.tving = Platform.objects.create(name='TVING', category=category)
        self.netflix_plan = SubscriptionPlan.objects.create(
            platform=self.netflix,
            plan_name='Standard',
            price=13500,
            billing_period='monthly',
        )
        self.tving_plan = SubscriptionPlan.objects.create(
            platform=self.tving,
            plan_name='Basic',
            price=9500,
            billing_period='monthly',
        )

    def _form_data(self, platform, plan):
        return {
            'platform': str(platform.id),
            'plan': str(plan.id),
            'plan_name': '',
            'payment_amount': '',
            'billing_cycle': '',
            'payment_method': '',
            'start_date': '2026-06-24',
            'renewal_date': '',
            'auto_renew': 'on',
            'memo': '',
        }

    def test_plan_options_include_platform_metadata(self):
        html = ManualSubscriptionForm().as_p()

        self.assertIn(f'data-platform="{self.netflix.id}"', html)
        self.assertIn(f'data-platform="{self.tving.id}"', html)

    def test_plan_must_belong_to_selected_platform(self):
        form = ManualSubscriptionForm(self._form_data(self.netflix, self.tving_plan))

        self.assertFalse(form.is_valid())
        self.assertIn('plan', form.errors)

    def test_selected_plan_autofills_missing_fields(self):
        form = ManualSubscriptionForm(self._form_data(self.netflix, self.netflix_plan))

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['plan_name'], 'Standard')
        self.assertEqual(form.cleaned_data['payment_amount'], 13500)


class ManualSubscriptionApiTest(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Streaming')
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='password',
        )
        self.netflix = Platform.objects.create(name='Netflix', category=category)
        self.plan = SubscriptionPlan.objects.create(
            platform=self.netflix,
            plan_name='Standard',
            price=13500,
            billing_period='monthly',
        )
        self.client.login(username='tester', password='password')

    def _payload(self):
        return {
            'platform': self.netflix.id,
            'plan': self.plan.id,
            'plan_name': self.plan.plan_name,
            'payment_amount': self.plan.price,
            'billing_cycle': self.plan.billing_period,
            'start_date': '2026-06-24',
            'renewal_date': '2026-07-24',
            'auto_renew': True,
        }

    def test_duplicate_active_platform_is_rejected(self):
        UserSubscription.objects.create(
            user=self.user,
            platform=self.netflix,
            plan=self.plan,
            plan_name=self.plan.plan_name,
            payment_amount=self.plan.price,
            billing_cycle=self.plan.billing_period,
            start_date='2026-06-24',
            renewal_date='2026-07-24',
        )

        response = self.client.post(
            '/api/accounts/subscriptions/',
            data=self._payload(),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(UserSubscription.objects.count(), 1)


class GoogleAuthIntentTest(TestCase):
    def test_oauth_start_stores_login_intent_in_session(self):
        response = self.client.get(
            '/accounts/auth/google/start/?intent=login&next=http://testserver/accounts/auth/google/done/',
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('google_auth_intent'), GOOGLE_AUTH_INTENT_LOGIN)

    def test_social_login_matches_existing_user_by_email(self):
        user = get_user_model().objects.create_user(
            username='member',
            email='member@example.com',
            password='password',
            nickname='Member',
        )
        sociallogin = SimpleNamespace(
            is_existing=False,
            user=SimpleNamespace(email=''),
            account=SimpleNamespace(
                provider='google',
                uid='google-uid-1',
                extra_data={'email': user.email},
            ),
        )

        self.assertTrue(social_login_matches_existing_user(sociallogin))
