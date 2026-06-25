"""Load a large Django JSON fixture in batches (CI-friendly progress logs)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsub.settings')

import django

django.setup()

from django.core.serializers import deserialize
from django.db import transaction


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: load_fixture_batched.py <fixture.json> [batch_size]', file=sys.stderr)
        return 1

    fixture_path = Path(sys.argv[1])
    if not fixture_path.is_file():
        print(f'fixture not found: {fixture_path}', file=sys.stderr)
        return 1

    batch_size = int(sys.argv[2] if len(sys.argv) > 2 else os.environ.get('FIXTURE_BATCH_SIZE', '150'))

    with fixture_path.open(encoding='utf-8') as handle:
        objects = list(deserialize('json', handle))

    total = len(objects)
    print(f'loading {fixture_path.name}: {total} objects (batch_size={batch_size})', flush=True)

    for start in range(0, total, batch_size):
        done = min(start + batch_size, total)
        print(f'  batch start: {start + 1}-{done}/{total}', flush=True)
        batch = objects[start:start + batch_size]
        with transaction.atomic():
            for item in batch:
                item.save()
        print(f'  progress: {done}/{total}', flush=True)

    print(f'loaded {total} objects from {fixture_path.name}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
