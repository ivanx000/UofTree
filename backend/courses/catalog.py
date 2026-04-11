import json
from urllib import parse, request


def _fetch_json(url, timeout=4):
    req = request.Request(url, headers={'User-Agent': 'UofTree/1.0'})
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def _normalize_course(code, payload):
    if not isinstance(payload, dict):
        return None

    normalized_code = (payload.get('code') or code or '').strip().upper()
    if not normalized_code:
        return None

    name = (
        payload.get('name')
        or payload.get('title')
        or payload.get('courseTitle')
        or 'Untitled Course'
    ).strip()

    description = (
        payload.get('description')
        or payload.get('courseDescription')
        or ''
    ).strip()

    return {
        'code': normalized_code,
        'name': name,
        'description': description,
    }


def search_timetable_courses(query, session, timeout=4, limit=25):
    """
    Search the UofT timetable API and return normalized course dicts.
    """
    q = (query or '').strip().upper()
    if not q:
        return []

    encoded = parse.urlencode({'code': q})
    url = f'https://timetable.iit.artsci.utoronto.ca/api/{session}/courses?{encoded}'
    data = _fetch_json(url, timeout=timeout)

    results = []
    # API returns a map keyed by course code.
    for code, payload in (data or {}).items():
        normalized = _normalize_course(code, payload)
        if not normalized:
            continue
        if q in normalized['code'] or q in normalized['name'].upper():
            results.append(normalized)

    results.sort(key=lambda c: c['code'])
    return results[:limit]


def fetch_timetable_course_by_code(code, session, timeout=4):
    """
    Fetch a single course by exact code from the UofT timetable API.
    """
    target = (code or '').strip().upper()
    if not target:
        return None

    encoded = parse.urlencode({'code': target})
    url = f'https://timetable.iit.artsci.utoronto.ca/api/{session}/courses?{encoded}'
    data = _fetch_json(url, timeout=timeout)

    for key, payload in (data or {}).items():
        normalized = _normalize_course(key, payload)
        if normalized and normalized['code'] == target:
            return normalized

    return None