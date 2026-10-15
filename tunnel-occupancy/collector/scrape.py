"""Fetch current NonStop Gym Tunnel occupancy from publicly embedded page data.

Requires: pip install requests
This does not circumvent Cloudflare or any access controls. If blocked, it fails
without recording a sample. The page embeds `var nsg_activity = {...};`.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

PAGE = 'https://www.nonstopgym.com/occupancy/'
START = re.compile(r'\b(?:var|let|const)\s+nsg_activity\s*=\s*', re.I)


def parse_tunnel(html):
    match = START.search(html)
    if not match:
        raise RuntimeError('Missing nsg_activity data in response (blocked page or changed website).')
    # JSONDecoder stops exactly at the end of the object; it does not confuse
    # braces inside strings with the end of the assignment.
    try:
        data, _ = json.JSONDecoder().raw_decode(html[match.end():].lstrip())
        value = data['gyms_data']['VAUD']['TUNNEL']['current']
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError('nsg_activity exists but Tunnel data could not be parsed.') from exc
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
        raise RuntimeError(f'Invalid Tunnel occupancy: {value!r}')
    return value


def fetch_tunnel():
    response = requests.get(PAGE, headers={
        'User-Agent': 'TunnelOccupancyResearch/1.0 (periodic personal gym capacity monitoring)',
        'Accept': 'text/html,application/xhtml+xml',
    }, timeout=30)
    print(f'NonStop Gym page HTTP status: {response.status_code}; bytes: {len(response.content)}', flush=True)
    if response.status_code in (403, 429, 503):
        raise RuntimeError(f'Source denied automated request (HTTP {response.status_code}); no sample stored.')
    response.raise_for_status()
    return parse_tunnel(response.text)


def save(value):
    endpoint = os.environ['SUPABASE_URL'].rstrip('/') + '/rest/v1/occupancy'
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    observed = datetime.now(timezone.utc).isoformat()
    resp = requests.post(endpoint, headers={
        'apikey': key, 'Authorization': 'Bearer ' + key,
        'Content-Type': 'application/json', 'Prefer': 'return=minimal',
    }, json={'observed_at': observed, 'percentage': value}, timeout=30)
    resp.raise_for_status()
    print(f'Stored {observed}: Tunnel {value}%', flush=True)


if __name__ == '__main__':
    val = fetch_tunnel()
    print(f'Extracted VAUD > TUNNEL: {val}%', flush=True)
    if '--dry-run' not in sys.argv:
        save(val)
