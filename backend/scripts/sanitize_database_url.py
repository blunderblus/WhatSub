"""Strip Supabase-only params from DATABASE_URL (safe for CI logs — prints boolean only)."""
from __future__ import annotations

import os
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def sanitize(url: str) -> str:
    url = url.strip().strip('"').strip("'")
    parsed = urlparse(url)
    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != 'pgbouncer'
    ]
    clean = urlunparse(parsed._replace(query=urlencode(kept)))
    clean = re.sub(r'([?&])pgbouncer(=[^&]*)?&?', r'\1', clean, flags=re.IGNORECASE)
    return clean.rstrip('?&')


def main() -> int:
    raw = os.environ.get('DATABASE_URL', '')
    if not raw:
        print('DATABASE_URL is empty', file=sys.stderr)
        return 1
    clean = sanitize(raw)
    print(f'pgbouncer_present_before={("pgbouncer" in raw.lower())}')
    print(f'pgbouncer_present_after={("pgbouncer" in clean.lower())}')
    # For GitHub Actions: write multiline-safe env
    github_env = os.environ.get('GITHUB_ENV')
    if github_env:
        with open(github_env, 'a', encoding='utf-8') as handle:
            handle.write('DATABASE_URL<<EOF\n')
            handle.write(clean + '\n')
            handle.write('EOF\n')
    else:
        print(clean)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
