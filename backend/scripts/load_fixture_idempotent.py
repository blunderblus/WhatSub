"""Load Django JSON fixtures with update_or_create (safe to re-run)."""
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

# Natural keys per model label — used for idempotent upsert on re-run.
UPSERT_KEYS: dict[str, tuple[str, ...]] = {
    'contents.platformbenchmarksnapshot': ('platform_id', 'snapshot_date'),
    'contents.platformgenrestats': ('platform_id', 'genre_id', 'snapshot_date'),
    'contents.streamingcache': ('tmdb_id', 'media_type', 'platform_id'),
    'contents.titlemeta': ('tmdb_id', 'media_type'),
    'contents.titlegenres': ('tmdb_id', 'media_type', 'genre_id'),
}


def _model_label(instance) -> str:
    meta = instance._meta
    return f'{meta.app_label}.{meta.model_name}'


def _field_value(instance, name: str):
    if name.endswith('_id'):
        fk = name[:-3]
        return getattr(instance, f'{fk}_id', None)
    return getattr(instance, name)


def _defaults(instance, exclude: set[str]) -> dict:
    meta = instance._meta
    data = {}
    for field in meta.fields:
        if field.primary_key or field.name in exclude:
            continue
        if field.many_to_many:
            continue
        data[field.name] = getattr(instance, field.name)
    return data


def save_idempotent(deserialized) -> None:
    instance = deserialized.object
    label = _model_label(instance)
    keys = UPSERT_KEYS.get(label)
    if not keys:
        instance.save()
        return

    lookup = {key: _field_value(instance, key) for key in keys}
    defaults = _defaults(instance, set(keys))
    instance._meta.model.objects.update_or_create(**lookup, defaults=defaults)


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: load_fixture_idempotent.py <fixture.json> [batch_size]', file=sys.stderr)
        return 1

    fixture_path = Path(sys.argv[1])
    if not fixture_path.is_file():
        print(f'fixture not found: {fixture_path}', file=sys.stderr)
        return 1

    batch_size = int(sys.argv[2] if len(sys.argv) > 2 else os.environ.get('FIXTURE_BATCH_SIZE', '150'))

    with fixture_path.open(encoding='utf-8') as handle:
        objects = list(deserialize('json', handle))

    total = len(objects)
    print(f'loading {fixture_path.name} (idempotent): {total} objects (batch_size={batch_size})', flush=True)

    for start in range(0, total, batch_size):
        done = min(start + batch_size, total)
        print(f'  batch start: {start + 1}-{done}/{total}', flush=True)
        batch = objects[start:start + batch_size]
        with transaction.atomic():
            for item in batch:
                save_idempotent(item)
        print(f'  progress: {done}/{total}', flush=True)

    print(f'loaded {total} objects from {fixture_path.name}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
