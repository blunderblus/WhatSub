from django.core.management.base import BaseCommand

from contents.benchmark_cache import aggregate_platform_genre_stats, run_cold_start


class Command(BaseCommand):
    help = (
        'Cold-start benchmark cache: fetch TMDB popular movie/TV titles, '
        'warm StreamingCache/TitleMeta/TitleGenres, then aggregate PlatformGenreStats.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--pages',
            type=int,
            default=5,
            help='Discover pages per media type (20 titles/page, default: 5)',
        )
        parser.add_argument(
            '--aggregate-only',
            action='store_true',
            help='Skip TMDB fetch; re-run PlatformGenreStats aggregation only',
        )

    def handle(self, *args, **options):
        pages = options['pages']

        if options['aggregate_only']:
            result = aggregate_platform_genre_stats()
            self.stdout.write(self.style.SUCCESS(f'Aggregation complete: {result}'))
            return

        self.stdout.write(f'Warming benchmark cache ({pages} pages x movie + tv)...')
        result = run_cold_start(pages=pages)
        warm = result['warm']
        agg = result['aggregate']

        self.stdout.write(self.style.SUCCESS(
            f"Done - titles: {warm['titles_processed']}, "
            f"TitleMeta: {warm['meta_upserted']}, "
            f"TitleGenres: {warm['genres_synced']}, "
            f"available StreamingCache rows: {warm['streaming_rows']}, "
            f"errors: {warm['errors']}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Genre stats - snapshot: {agg['snapshot_date']}, "
            f"rows: {agg['platform_genre_rows']}, "
            f"distinct titles: {agg['total_titles_in_cache']}"
        ))
