import logging

from django.core.management.base import BaseCommand

from contents.cache_warming import warm_cache

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Cold-start cache warming: stage1 genre-balanced + stage2 KR platform-targeted. '
        'TitleMeta/TitleGenres update, StreamingCache via RapidAPI + TMDB (Watchmode disabled).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-rapidapi',
            action='store_true',
            help='Skip RapidAPI (use when quota/rate-limited); TMDB watch providers fallback only',
        )

    def handle(self, *args, **options):
        def log(msg, *log_args):
            if log_args:
                msg = msg % log_args
            self.stdout.write(msg)
            logger.info(msg)

        skip_rapidapi = options['skip_rapidapi']
        if skip_rapidapi:
            log('[warm_cache] RapidAPI skipped - TMDB providers only')
        summary = warm_cache(log=log, skip_rapidapi=skip_rapidapi)

        s1 = summary['stage1']
        s2 = summary['stage2']

        log('')
        log('[warm_cache] === summary ===')
        log(
            '  1단계 (장르 균형): 유니크 타이틀 %d개, '
            'fetch %d, failed %d, skip fresh %d',
            s1['unique_titles'],
            s1['availability_fetches'],
            s1.get('availability_failed', 0),
            s1['skipped_fresh'],
        )
        log(
            '  2단계 (국내 플랫폼 보강): 유니크 타이틀 %d개, '
            'fetch %d, failed %d, skip fresh %d',
            s2['unique_titles'],
            s2['availability_fetches'],
            s2.get('availability_failed', 0),
            s2['skipped_fresh'],
        )
        log(
            '  전체 합계: 유니크 타이틀 %d개, availability fetch %d회',
            summary['total_unique_titles'],
            summary['total_availability_fetches'],
        )
        log('  titles per platform:')
        for row in summary['platform_counts']:
            log('    %s: %d', row['platform__name'], row['title_count'])

        total_errors = s1['errors'] + s2['errors']
        if total_errors:
            self.stdout.write(self.style.WARNING(
                f'[warm_cache] finished with {total_errors} error(s)'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('[warm_cache] finished OK'))
