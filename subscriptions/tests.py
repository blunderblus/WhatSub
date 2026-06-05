from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import (
    Category, Platform, SubscriptionPlan,
    BundleContent, AddOnPass, AddOnPassPricing,
)


# ─── Model Integrity Tests ────────────────────────────────────────────────────

class ModelCountTest(TestCase):
    """Verify seeded object counts."""
    fixtures = ['platform_seed']

    def test_category_count(self):
        self.assertEqual(Category.objects.count(), 4)

    def test_platform_count(self):
        self.assertEqual(Platform.objects.count(), 16)

    def test_subscription_plan_count(self):
        self.assertEqual(SubscriptionPlan.objects.count(), 41)

    def test_bundle_content_count(self):
        self.assertEqual(BundleContent.objects.count(), 23)

    def test_addon_pass_count(self):
        self.assertEqual(AddOnPass.objects.count(), 6)

    def test_addon_pass_pricing_count(self):
        self.assertEqual(AddOnPassPricing.objects.count(), 12)


class TVINGPriceTest(TestCase):
    """TVING prices were corrected from stale values — verify."""
    fixtures = ['platform_seed']

    def test_monthly_prices(self):
        plans = {
            p.plan_name: p.price
            for p in SubscriptionPlan.objects.filter(
                platform__name='TVING', billing_period='monthly',
            )
        }
        self.assertEqual(plans['베이직'], 9500)
        self.assertEqual(plans['스탠다드'], 13500)
        self.assertEqual(plans['프리미엄'], 17000)
        self.assertEqual(plans['광고형 스탠다드'], 5500)

    def test_annual_plans_exist(self):
        annual = SubscriptionPlan.objects.filter(
            platform__name='TVING', billing_period='annual',
        )
        self.assertEqual(annual.count(), 3)
        prices = set(annual.values_list('price', flat=True))
        self.assertEqual(prices, {95000, 135000, 169000})

    def test_광고형_quality_and_streams(self):
        plan = SubscriptionPlan.objects.get(
            platform__name='TVING',
            plan_name='광고형 스탠다드',
            billing_period='monthly',
        )
        self.assertEqual(plan.max_quality, 'FHD')
        self.assertEqual(plan.max_streams, 2)


class AnnualPlansTest(TestCase):
    fixtures = ['platform_seed']

    def test_wavve_annual(self):
        annual = SubscriptionPlan.objects.filter(
            platform__name='Wavve', billing_period='annual',
        )
        self.assertEqual(annual.count(), 3)
        prices = set(annual.values_list('price', flat=True))
        self.assertEqual(prices, {79000, 109000, 139000})

    def test_watcha_annual(self):
        annual = SubscriptionPlan.objects.filter(
            platform__name='Watcha', billing_period='annual',
        )
        self.assertEqual(annual.count(), 2)
        prices = set(annual.values_list('price', flat=True))
        self.assertEqual(prices, {79900, 129900})


class RequiresMembershipTest(TestCase):
    fixtures = ['platform_seed']

    def test_coupang_play_wow_requires_coupang_wow(self):
        wow = SubscriptionPlan.objects.get(
            platform__name='Coupang Play', plan_name='와우',
        )
        self.assertIsNotNone(wow.requires_membership)
        self.assertEqual(wow.requires_membership.plan_name, '와우 멤버십')
        self.assertEqual(wow.requires_membership.platform.name, 'Coupang')

    def test_other_plans_have_no_requirement(self):
        no_req = SubscriptionPlan.objects.exclude(
            platform__name='Coupang Play', plan_name='와우',
        ).filter(requires_membership__isnull=False)
        self.assertEqual(no_req.count(), 0)


class BundleContentTest(TestCase):
    fixtures = ['platform_seed']

    def test_apple_one_개인_includes_4_platforms(self):
        plan = SubscriptionPlan.objects.get(platform__name='Apple One', plan_name='개인')
        self.assertTrue(plan.is_bundle)
        included = set(
            plan.bundle_contents.values_list('included_platform__name', flat=True)
        )
        self.assertEqual(included, {'Apple TV+', 'Apple Music', 'Apple Arcade', 'iCloud+'})

    def test_apple_one_가족_includes_4_platforms(self):
        plan = SubscriptionPlan.objects.get(platform__name='Apple One', plan_name='가족')
        self.assertEqual(plan.bundle_contents.count(), 4)

    def test_3pack_includes_disney_tving_wavve(self):
        pack = SubscriptionPlan.objects.get(plan_name__contains='3PACK')
        included = set(
            pack.bundle_contents.values_list('included_platform__name', flat=True)
        )
        self.assertEqual(included, {'Disney+', 'TVING', 'Wavve'})

    def test_double_includes_disney_tving(self):
        double = SubscriptionPlan.objects.get(plan_name__contains='더블')
        included = set(
            double.bundle_contents.values_list('included_platform__name', flat=True)
        )
        self.assertEqual(included, {'Disney+', 'TVING'})

    def test_tving_wavve_bundles_all_include_both_platforms(self):
        bundles = SubscriptionPlan.objects.filter(
            platform__name='OTT 번들', plan_name__contains='TVING×Wavve',
        )
        for bundle in bundles:
            included = set(
                bundle.bundle_contents.values_list('included_platform__name', flat=True)
            )
            self.assertIn('TVING', included, msg=f'{bundle.plan_name} missing TVING')
            self.assertIn('Wavve', included, msg=f'{bundle.plan_name} missing Wavve')


class AddOnPassTest(TestCase):
    fixtures = ['platform_seed']

    def test_coupang_play_has_6_passes(self):
        passes = AddOnPass.objects.filter(platform__name='Coupang Play')
        self.assertEqual(passes.count(), 6)
        names = set(passes.values_list('pass_name', flat=True))
        self.assertIn('스포츠 패스', names)
        self.assertIn('J PLUS 패스', names)
        self.assertIn('파라마운트+ 패스', names)
        self.assertIn('MOA 패스', names)
        self.assertIn('EBS 패스', names)
        self.assertIn('소니 픽처스 패스', names)

    def test_sports_pass_tiered_pricing(self):
        regular = AddOnPassPricing.objects.get(
            addon_pass__pass_name='스포츠 패스', base_plan__plan_name='일반',
        )
        member = AddOnPassPricing.objects.get(
            addon_pass__pass_name='스포츠 패스', base_plan__plan_name='와우',
        )
        self.assertEqual(regular.price, 16600)
        self.assertEqual(member.price, 9900)
        self.assertGreater(regular.price, member.price)

    def test_all_passes_have_two_pricing_tiers(self):
        for addon in AddOnPass.objects.all():
            self.assertEqual(
                addon.pricings.count(), 2,
                msg=f'{addon.pass_name} should have 2 pricing tiers',
            )


class NotesFieldTest(TestCase):
    fixtures = ['platform_seed']

    def test_tving_premium_notes_contain_affiliate_and_app_price(self):
        plan = SubscriptionPlan.objects.get(
            platform__name='TVING', plan_name='프리미엄', billing_period='monthly',
        )
        self.assertIn('app_price', plan.notes)
        self.assertIn('includes_apple_tv_plus', plan.notes)
        self.assertIn('affiliate_T', plan.notes)

    def test_amazon_prime_usd_note(self):
        plan = SubscriptionPlan.objects.get(platform__name='Amazon Prime Video')
        self.assertIn('USD_PRICE=6', plan.notes)
        self.assertEqual(plan.price, 8700)

    def test_apple_tv_free_trial_note(self):
        plan = SubscriptionPlan.objects.get(platform__name='Apple TV+', plan_name='단독')
        self.assertIn('free_trial_days=7', plan.notes)

    def test_coupang_play_일반_content_access_note(self):
        plan = SubscriptionPlan.objects.get(
            platform__name='Coupang Play', plan_name='일반',
        )
        self.assertIn('content_access=limited', plan.notes)


# ─── API Tests ────────────────────────────────────────────────────────────────

class PlatformAPITest(APITestCase):
    fixtures = ['platform_seed']

    def test_platform_list_status_and_count(self):
        url = reverse('subscriptions:platform_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 16)

    def test_platform_list_contains_expected_names(self):
        url = reverse('subscriptions:platform_list')
        response = self.client.get(url)
        names = {p['name'] for p in response.data}
        for expected in ('Netflix', 'Disney+', 'TVING', 'Wavve', 'Watcha',
                         'Coupang Play', 'Amazon Prime Video', 'SPOTV', 'Laftel',
                         'Apple One', 'OTT 번들'):
            self.assertIn(expected, names)

    def test_platform_detail_includes_nested_plans(self):
        tving = Platform.objects.get(name='TVING')
        url = reverse('subscriptions:platform_detail', kwargs={'pk': tving.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan_names = {p['plan_name'] for p in response.data['plans']}
        self.assertIn('베이직', plan_names)
        self.assertIn('스탠다드', plan_names)
        self.assertIn('프리미엄', plan_names)
        self.assertIn('광고형 스탠다드', plan_names)

    def test_platform_detail_coupang_play_has_addon_passes(self):
        cp = Platform.objects.get(name='Coupang Play')
        url = reverse('subscriptions:platform_detail', kwargs={'pk': cp.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['addon_passes']), 6)

    def test_platform_detail_passes_have_pricings(self):
        cp = Platform.objects.get(name='Coupang Play')
        url = reverse('subscriptions:platform_detail', kwargs={'pk': cp.pk})
        response = self.client.get(url)
        for p in response.data['addon_passes']:
            self.assertEqual(
                len(p['pricings']), 2,
                msg=f"{p['pass_name']} should have 2 pricing tiers",
            )

    def test_platform_detail_requires_membership_name(self):
        cp = Platform.objects.get(name='Coupang Play')
        url = reverse('subscriptions:platform_detail', kwargs={'pk': cp.pk})
        response = self.client.get(url)
        wow_plan = next(p for p in response.data['plans'] if p['plan_name'] == '와우')
        self.assertIsNotNone(wow_plan['requires_membership_name'])
        self.assertIn('와우 멤버십', wow_plan['requires_membership_name'])

    def test_platform_detail_404_for_invalid_pk(self):
        url = reverse('subscriptions:platform_detail', kwargs={'pk': 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PlanAPITest(APITestCase):
    fixtures = ['platform_seed']

    def test_plan_list_total_count(self):
        url = reverse('subscriptions:plan_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 41)

    def test_plan_list_filter_by_platform(self):
        tving = Platform.objects.get(name='TVING')
        url = reverse('subscriptions:plan_list') + f'?platform={tving.pk}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 7)  # 4 monthly + 3 annual

    def test_plan_list_filter_annual(self):
        url = reverse('subscriptions:plan_list') + '?billing=annual'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 8)  # TVING×3 + Wavve×3 + Watcha×2
        for plan in response.data:
            self.assertEqual(plan['billing_period'], 'annual')

    def test_plan_list_filter_bundle_true(self):
        url = reverse('subscriptions:plan_list') + '?bundle=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 9)  # 2 Apple One + 5 TVING×Wavve + 2 Disney+
        for plan in response.data:
            self.assertTrue(plan['is_bundle'])

    def test_plan_list_filter_bundle_false(self):
        url = reverse('subscriptions:plan_list') + '?bundle=false'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 32)  # 41 total - 9 bundles
        for plan in response.data:
            self.assertFalse(plan['is_bundle'])

    def test_bundle_contents_in_plan_list(self):
        url = reverse('subscriptions:plan_list') + '?bundle=true'
        response = self.client.get(url)
        pack = next(p for p in response.data if '3PACK' in p['plan_name'])
        included_names = {bc['included_platform_name'] for bc in pack['bundle_contents']}
        self.assertEqual(included_names, {'Disney+', 'TVING', 'Wavve'})


class BundleAPITest(APITestCase):
    fixtures = ['platform_seed']

    def test_bundle_list_returns_only_bundles(self):
        url = reverse('subscriptions:bundle_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 9)
        for plan in response.data:
            self.assertTrue(plan['is_bundle'])

    def test_bundle_list_ordered_by_price(self):
        url = reverse('subscriptions:bundle_list')
        response = self.client.get(url)
        prices = [p['price'] for p in response.data]
        self.assertEqual(prices, sorted(prices))


class AddonPassAPITest(APITestCase):
    fixtures = ['platform_seed']

    def test_addon_pass_list_total(self):
        url = reverse('subscriptions:addon_pass_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)

    def test_addon_pass_filter_by_platform(self):
        cp = Platform.objects.get(name='Coupang Play')
        url = reverse('subscriptions:addon_pass_list') + f'?platform={cp.pk}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)

    def test_addon_pass_pricings_nested(self):
        url = reverse('subscriptions:addon_pass_list')
        response = self.client.get(url)
        for addon in response.data:
            self.assertIn('pricings', addon)
            self.assertEqual(
                len(addon['pricings']), 2,
                msg=f"{addon['pass_name']} should have 2 pricing tiers",
            )

    def test_sports_pass_price_values(self):
        url = reverse('subscriptions:addon_pass_list')
        response = self.client.get(url)
        sports = next(a for a in response.data if a['pass_name'] == '스포츠 패스')
        prices = {p['base_plan_name'].split(' - ')[1]: p['price'] for p in sports['pricings']}
        self.assertEqual(prices['일반'], 16600)
        self.assertEqual(prices['와우'], 9900)
