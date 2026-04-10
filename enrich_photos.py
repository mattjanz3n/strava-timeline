#!/usr/bin/env python3
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIVITIES_JSON = ROOT / 'activities.json'
ACTIVITIES_JS = ROOT / 'activities.js'
TOKEN_JSON = ROOT / 'token.json'


def load_json(path: Path):
    return json.loads(path.read_text())


def fetch_activity(activity_id: int, token: str):
    req = urllib.request.Request(
        f'https://www.strava.com/api/v3/activities/{activity_id}?include_all_efforts=false'
    )
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def extract_photo_fields(full_activity: dict):
    photos = full_activity.get('photos') or {}
    primary = photos.get('primary') or {}
    urls = primary.get('urls') or {}
    return {
        'photoPreviewUrl': urls.get('600') or urls.get('100'),
        'photoThumbUrl': urls.get('100') or urls.get('600'),
        'photoMediaType': primary.get('media_type'),
        'photoUniqueId': primary.get('unique_id'),
        'photoCount': photos.get('count') or full_activity.get('total_photo_count') or 0,
    }


def main():
    activities = load_json(ACTIVITIES_JSON)
    token = load_json(TOKEN_JSON).get('access_token')
    if not token:
        print('No access token found in token.json', file=sys.stderr)
        return 1

    targets = [
        a for a in activities
        if (a.get('total_photo_count', 0) or a.get('hasPhoto')) and not a.get('photoPreviewUrl')
    ]
    print(f'Found {len(targets)} activities needing photo enrichment')

    updated = 0
    for idx, activity in enumerate(targets, start=1):
        aid = activity['id']
        try:
            full = fetch_activity(aid, token)
            photo_fields = extract_photo_fields(full)
            activity.update(photo_fields)
            updated += 1
            print(f'[{idx}/{len(targets)}] enriched {aid}: {photo_fields.get("photoPreviewUrl") or "no preview URL"}')
            time.sleep(0.2)
        except Exception as exc:
            print(f'[{idx}/{len(targets)}] failed {aid}: {exc}', file=sys.stderr)

    ACTIVITIES_JSON.write_text(json.dumps(activities, indent=2) + '\n')
    ACTIVITIES_JS.write_text('window.STRAVA_ACTIVITIES = ' + json.dumps(activities) + ';\n')
    print(f'Updated {updated} activities')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
