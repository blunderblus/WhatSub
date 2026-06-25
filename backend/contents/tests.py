from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from unittest.mock import patch

from subscriptions.models import Platform
from . import views
from .image_urls import find_nested_image_url, tmdb_image_url
from .models import Content, ContentPlatform
from .streaming_provider_display import decorate_providers, provider_key, sort_providers


class ContentModelTest(TestCase):
    fixtures = ['platform_seed']

    def setUp(self):
        self.content = Content.objects.create(
            tmdb_id=550,
            title='Fight Club',
            korean_title='파이트 클럽',
            overview='An insomniac office worker...',
            content_type='movie',
            rating=8.4,
        )

    def test_content_str(self):
        self.assertEqual(str(self.content), '파이트 클럽')

    def test_content_str_falls_back_to_title(self):
        content = Content.objects.create(tmdb_id=551, title='No Korean Title', content_type='movie')
        self.assertEqual(str(content), 'No Korean Title')

    def test_watchmode_id_nullable(self):
        self.assertIsNone(self.content.watchmode_id)
        self.content.watchmode_id = 12345
        self.content.save()
        self.assertEqual(Content.objects.get(pk=self.content.pk).watchmode_id, 12345)

    def test_sources_synced_at_nullable(self):
        self.assertIsNone(self.content.sources_synced_at)

    def test_tmdb_id_unique(self):
        with self.assertRaises(Exception):
            Content.objects.create(tmdb_id=550, title='Duplicate', content_type='movie')


class ContentPlatformTest(TestCase):
    fixtures = ['platform_seed']

    def setUp(self):
        self.content = Content.objects.create(
            tmdb_id=680,
            title='Pulp Fiction',
            korean_title='펄프 픽션',
            content_type='movie',
        )
        self.netflix = Platform.objects.get(name='Netflix')
        self.tving = Platform.objects.get(name='TVING')

    def test_create_subscription_source(self):
        cp = ContentPlatform.objects.create(
            content=self.content,
            platform=self.netflix,
            source_type=ContentPlatform.SourceType.SUB,
            deeplink_url='https://www.netflix.com/watch/70058107',
        )
        self.assertEqual(cp.source_type, 'sub')
        self.assertTrue(cp.is_available)

    def test_create_rent_source_with_price(self):
        cp = ContentPlatform.objects.create(
            content=self.content,
            platform=self.netflix,
            source_type=ContentPlatform.SourceType.RENT,
            price=3500,
        )
        self.assertEqual(cp.price, 3500)

    def test_unique_together_content_platform_source_type(self):
        ContentPlatform.objects.create(
            content=self.content,
            platform=self.netflix,
            source_type=ContentPlatform.SourceType.SUB,
        )
        with self.assertRaises(IntegrityError):
            ContentPlatform.objects.create(
                content=self.content,
                platform=self.netflix,
                source_type=ContentPlatform.SourceType.SUB,
            )

    def test_same_platform_different_source_types_allowed(self):
        ContentPlatform.objects.create(
            content=self.content, platform=self.netflix,
            source_type=ContentPlatform.SourceType.SUB,
        )
        ContentPlatform.objects.create(
            content=self.content, platform=self.netflix,
            source_type=ContentPlatform.SourceType.RENT,
            price=3500,
        )
        self.assertEqual(
            ContentPlatform.objects.filter(content=self.content, platform=self.netflix).count(),
            2,
        )

    def test_multiple_platforms_for_same_content(self):
        ContentPlatform.objects.create(
            content=self.content, platform=self.netflix,
            source_type=ContentPlatform.SourceType.SUB,
        )
        ContentPlatform.objects.create(
            content=self.content, platform=self.tving,
            source_type=ContentPlatform.SourceType.SUB,
        )
        self.assertEqual(
            ContentPlatform.objects.filter(content=self.content).count(), 2,
        )

    def test_source_type_choices(self):
        valid_types = {c[0] for c in ContentPlatform.SourceType.choices}
        self.assertEqual(valid_types, {'sub', 'rent', 'buy', 'free'})

    def test_content_platform_str(self):
        cp = ContentPlatform.objects.create(
            content=self.content, platform=self.netflix,
            source_type=ContentPlatform.SourceType.SUB,
        )
        self.assertIn('Netflix', str(cp))
        self.assertIn('sub', str(cp))


class ProviderDisplayUtilityTest(TestCase):
    def test_provider_key_normalizes_known_aliases(self):
        self.assertEqual(
            provider_key({'service': 'disneyplus', 'type': 'subscription'}),
            ('disney+', 'subscription'),
        )

    def test_sort_providers_uses_provider_priority_then_service_name(self):
        providers = [
            {'service': 'Watcha', 'type': 'rent'},
            {'service': 'Netflix', 'type': 'subscription'},
            {'service': 'TVING', 'type': 'free'},
        ]

        self.assertEqual(
            [p['service'] for p in sort_providers(providers)],
            ['Netflix', 'TVING', 'Watcha'],
        )

    def test_decorate_providers_adds_local_icon_for_known_service(self):
        [provider] = decorate_providers([{'service': 'coupangplay'}])

        self.assertEqual(provider['display_name'], 'Coupang Play')
        self.assertTrue(provider['icon_url'].endswith('/media/CoupangPlay_icon.png'))
        self.assertTrue(provider['icon_url'].startswith('http'))

    def test_tmdb_image_url_builds_expected_url(self):
        self.assertEqual(
            tmdb_image_url('/poster.png', 'w500'),
            'https://image.tmdb.org/t/p/w500/poster.png',
        )

    def test_find_nested_image_url_returns_first_supported_image_key(self):
        payload = {
            'service': {
                'darkThemeImage': 'https://example.com/dark.png',
            },
        }

        self.assertEqual(
            find_nested_image_url(payload),
            'https://example.com/dark.png',
        )


class StreamingProviderCacheTest(TestCase):
    fixtures = ['platform_seed']

    def setUp(self):
        self.content = Content.objects.create(
            tmdb_id=777001,
            title='Cached Title',
            content_type='movie',
            sources_cache=[{
                'service': 'Netflix',
                'display_name': 'Netflix',
                'type': 'subscription',
                'type_label': '구독',
                'source': 'tmdb',
            }],
            sources_synced_at=timezone.now(),
        )

    def test_fresh_sources_cache_returns_without_paid_availability_calls(self):
        with (
            patch.object(views, '_providers_from_tmdb_watch') as tmdb_watch,
            patch.object(views, '_fetch_streaming_availability') as rapidapi,
            patch.object(views.wm, 'resolve_watchmode_id') as watchmode_resolve,
            patch.object(views.wm, 'fetch_sources') as watchmode_sources,
            patch.object(views.wm, 'is_configured', return_value=True),
            patch.object(views.WatchmodeUsage, 'can_call', return_value=True),
        ):
            providers = views.get_streaming_providers(
                self.content.tmdb_id,
                'movie',
                allow_watchmode=True,
                allow_rapidapi_fallback=True,
                skip_rapidapi=True,
            )

        self.assertEqual([provider['service'] for provider in providers], ['Netflix'])
        tmdb_watch.assert_not_called()
        rapidapi.assert_not_called()
        watchmode_resolve.assert_not_called()
        watchmode_sources.assert_not_called()
