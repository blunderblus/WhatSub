import logging

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from contents.benchmark_scoring import run_benchmark_batch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Monthly benchmark batch: aggregate genre stats, compute 5-axis scores '
        '(availability, exclusivity, quality, price, accessibility), '
        'write PlatformBenchmarkSnapshot.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--snapshot-date',
            type=str,
            default=None,
            help='Snapshot date YYYY-MM-DD (default: today)',
        )
        parser.add_argument(
            '--skip-llm',
            action='store_true',
            help='Skip LLM calls (use heuristic defaults for exclusivity/price)',
        )

    def handle(self, *args, **options):
        def log(msg, *log_args):
            if log_args:
                msg = msg % log_args
            self.stdout.write(msg)
            logger.info(msg)

        snapshot_date = None
        if options['snapshot_date']:
            snapshot_date = parse_date(options['snapshot_date'])
            if not snapshot_date:
                self.stderr.write(self.style.ERROR('Invalid --snapshot-date format'))
                return

        use_llm = not options['skip_llm']
        if options['skip_llm']:
            log('[benchmark] LLM skipped - using heuristic exclusivity/price scoring')

        log('[benchmark] batch started')
        summary = run_benchmark_batch(
            snapshot_date=snapshot_date,
            use_llm=use_llm,
            log=log,
        )

        log('')
        log('[benchmark] === snapshot %s ===', summary['snapshot_date'])
        log('[benchmark] global cache titles: %d', summary['global_titles'])
        log('[benchmark] platform scores (value desc):')
        for row in summary['platforms']:
            log(
                '  %s: value=%.3f conf=%s avail=%.2f excl=%.2f qual=%.2f price=%.2f acc=%.2f titles=%d',
                row['name'], row['value_score'], row['confidence'],
                row['availability'], row['exclusivity'], row['quality'],
                row['price'], row['accessibility'], row['titles'],
            )

        self.stdout.write(self.style.SUCCESS('[benchmark] batch finished OK'))
