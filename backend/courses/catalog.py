import json
import re
import xml.etree.ElementTree as ET
from html import unescape
from urllib import parse, request

# Matches UofT course codes like CSC148H1, MAT237Y1, ECE344H1
_COURSE_CODE_RE = re.compile(r'\b[A-Z]{2,6}\d{3}[HY]\d\b')

_EASI_BASE = 'https://api.easi.utoronto.ca/ttb'
_EASI_HEADERS = {
    'Content-Type': 'application/json',
    'Origin': 'https://ttb.utoronto.ca',
    'Referer': 'https://ttb.utoronto.ca/',
    'User-Agent': 'UofTree/1.0',
}


# ── Session helpers ────────────────────────────────────────────────────────────

def _session_variants(session):
    """
    Given a session code like '20261' (Winter) or '20259' (Fall), return a
    list of related session codes to cover the full academic year.

    EASI codes:
      YYYY9  = Fall (Sep)
      YYYY1  = Winter (Jan) of the following calendar year
      YYYY9-ZZZZ1  = Full-year spanning both
    """
    s = str(session)
    if s.endswith('1'):
        # Winter session — also include the preceding fall and the combined year
        year = int(s[:4])
        fall = f'{year - 1}9'
        return [fall, s, f'{fall}-{s}']
    elif s.endswith('9'):
        # Fall session — also include the following winter and combined year
        year = int(s[:4])
        winter = f'{year + 1}1'
        return [s, winter, f'{s}-{winter}']
    return [s]


# ── Low-level HTTP helpers ─────────────────────────────────────────────────────

def _get_json(url, timeout=4):
    req = request.Request(url, headers=_EASI_HEADERS)
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _post_xml(url, body, timeout=4):
    data = json.dumps(body).encode('utf-8')
    req = request.Request(url, data=data, headers=_EASI_HEADERS)
    with request.urlopen(req, timeout=timeout) as resp:
        return ET.fromstring(resp.read().decode('utf-8'))


def _easi_status_ok(root):
    """Return True if the EASI XML response has a success status code."""
    code = root.findtext('.//status/status/code', '')
    return code == '0'


# ── Course parsing ─────────────────────────────────────────────────────────────

def extract_prerequisite_codes(text):
    """
    Parse a free-text prerequisite string and return the list of course codes
    found within it.  E.g. "CSC108H1 or CSC150H1" → ['CSC148H1', 'CSC150H1'].
    """
    if not text:
        return []
    return _COURSE_CODE_RE.findall(text.upper())


def _parse_course_element(elem):
    """
    Parse a single <courses> XML element from a getPageableCourses response
    into a normalised dict with keys: code, name, description, prerequisite_codes.
    """
    code = (elem.findtext('code') or '').strip().upper()
    if not code:
        return None

    name = (elem.findtext('name') or 'Untitled Course').strip()

    cm = elem.find('cmCourseInfo')
    if cm is not None:
        description = (cm.findtext('description') or '').strip()
        raw_prereq = (cm.findtext('prerequisitesText') or '').strip()
    else:
        description = ''
        raw_prereq = ''

    # prerequisitesText comes back as HTML-escaped HTML; strip tags after unescaping
    prereq_text = re.sub(r'<[^>]+>', ' ', unescape(raw_prereq)).strip()

    return {
        'code': code,
        'name': name,
        'description': description,
        'prerequisite_codes': extract_prerequisite_codes(prereq_text),
    }


# ── Department lookup ──────────────────────────────────────────────────────────

def _get_dept_props(dept_prefix, timeout=4):
    """
    Return a list of departmentProp dicts for the given dept prefix (e.g. 'CSC').
    Each dict has keys: division, department, type — ready to drop into the
    getPageableCourses departmentProps array.

    Returns [] if the prefix is not found or the request fails.
    """
    encoded = parse.urlencode({'term': dept_prefix, 'divisions': ''})
    url = f'{_EASI_BASE}/getMatchingDepartments?{encoded}'
    try:
        req = request.Request(url, headers=_EASI_HEADERS)
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8')
    except Exception:
        return []

    # The XML uses faculty names as tag names (spaces allowed in this API's XML),
    # so we parse dept blocks with regex rather than ElementTree for this endpoint.
    # Each block looks like: <code>CSC</code><type>DEPARTMENT</type><faculty><code>ARTSC</code>…
    props = []
    prefix_upper = dept_prefix.strip().upper()
    for m in re.finditer(
        r'<code>([^<]+)</code><type>([^<]+)</type><faculty><code>([^<]+)</code>',
        raw,
    ):
        code, dtype, division = m.group(1), m.group(2), m.group(3)
        if code.upper().startswith(prefix_upper):
            props.append({'division': division, 'department': code, 'type': dtype})

    return props


# ── getPageableCourses wrapper ─────────────────────────────────────────────────

def _pageable_courses(body, timeout=8):
    """
    POST to getPageableCourses and return a list of parsed course dicts.
    Returns [] on any error or empty result.
    """
    url = f'{_EASI_BASE}/getPageableCourses'
    try:
        root = _post_xml(url, body, timeout=timeout)
    except Exception:
        return []

    if not _easi_status_ok(root):
        return []

    results = []
    for elem in root.findall('.//pageableCourse/courses/courses'):
        parsed = _parse_course_element(elem)
        if parsed:
            results.append(parsed)
    return results


def _base_body(sessions):
    """Return the minimal getPageableCourses request body."""
    return {
        'courseCodeAndTitleProps': {
            'courseCode': '',
            'courseTitle': '',
            'courseSectionCode': '',
            'searchCourseDescription': False,
        },
        'departmentProps': [],
        'campuses': [],
        'sessions': sessions,
        'requirementProps': [],
        'instructor': '',
        'courseLevels': [],
        'deliveryModes': [],
        'dayPreferences': [],
        'timePreferences': [],
        'divisions': [],
        'creditWeights': [],
        'page': 1,
        'pageSize': 100,
        'direction': 'asc',
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_timetable_courses_by_prefix(dept_prefix, session, timeout=10):
    """
    Fetch all courses for a department prefix (e.g. 'CSC', 'MAT') using the
    EASI timetable API.

    Returns a dict keyed by course code so import_courses can normalise and
    avoid double network round-trips.  On failure returns {}.
    """
    prefix = (dept_prefix or '').strip().upper()
    if not prefix:
        return {}

    dept_props = _get_dept_props(prefix, timeout=timeout)
    if not dept_props:
        return {}

    sessions = _session_variants(session)
    result = {}

    for dept_prop in dept_props:
        # Paginate to collect all courses in this department
        page = 1
        while True:
            body = _base_body(sessions)
            body['departmentProps'] = [dept_prop]
            body['pageSize'] = 100
            body['page'] = page

            url = f'{_EASI_BASE}/getPageableCourses'
            try:
                root = _post_xml(url, body, timeout=timeout)
            except Exception:
                break

            if not _easi_status_ok(root):
                break

            courses_on_page = root.findall('.//pageableCourse/courses/courses')
            if not courses_on_page:
                break

            for elem in courses_on_page:
                parsed = _parse_course_element(elem)
                if parsed:
                    result[parsed['code']] = parsed

            # Check if there are more pages
            total_text = root.findtext('.//pageableCourse/total') or '0'
            try:
                total = int(total_text)
            except ValueError:
                total = 0

            if page * 100 >= total:
                break
            page += 1

    return result


def search_timetable_courses(query, session, timeout=4, limit=25):
    """
    Search the EASI timetable API for courses matching a query string.

    Strategy:
      1. If the query looks like a department prefix (letters only, ≤ 6 chars),
         look up matching departments and fetch their courses.
      2. Otherwise, search by course title.

    Returns a list of normalised course dicts sorted by code.
    """
    q = (query or '').strip().upper()
    if not q:
        return []

    sessions = _session_variants(session)

    def _dedup(courses):
        seen = {}
        for c in courses:
            if c['code'] not in seen:
                seen[c['code']] = c
        return sorted(seen.values(), key=lambda c: c['code'])

    # --- Strategy 1: department prefix (e.g. "CSC", "MAT", "ECE") ---
    if re.fullmatch(r'[A-Z]{2,6}', q):
        dept_props = _get_dept_props(q, timeout=timeout)
        if dept_props:
            body = _base_body(sessions)
            body['departmentProps'] = dept_props
            body['pageSize'] = limit * 4  # over-fetch to survive dedup
            results = _dedup(_pageable_courses(body, timeout=timeout))
            return results[:limit]

    # --- Strategy 2: partial code like "CSC1" or "CSC148" ---
    if re.fullmatch(r'[A-Z]{2,6}\d{1,3}[HY]?\d?', q):
        dept_match = re.match(r'([A-Z]{2,6})', q)
        if dept_match:
            dept_props = _get_dept_props(dept_match.group(1), timeout=timeout)
            if dept_props:
                body = _base_body(sessions)
                body['departmentProps'] = dept_props
                body['pageSize'] = 200
                all_courses = _dedup(_pageable_courses(body, timeout=timeout))
                return [c for c in all_courses if q in c['code']][:limit]

    # --- Strategy 3: title/keyword search ---
    body = _base_body(sessions)
    body['courseCodeAndTitleProps']['courseTitle'] = q.lower()
    body['pageSize'] = limit * 4
    results = _dedup(_pageable_courses(body, timeout=timeout))
    return results[:limit]


def fetch_timetable_course_by_code(code, session, timeout=4):
    """
    Fetch a single course by code from the EASI timetable API.

    Handles both full codes (CSC148H1) and partial codes (CSC148) by trying
    common suffixes when an exact match isn't found.
    """
    target = (code or '').strip().upper()
    if not target:
        return None

    sessions = _session_variants(session)

    def _try_exact(c):
        body = _base_body(sessions)
        body['courseCodeAndTitleProps']['courseCode'] = c
        body['pageSize'] = 10
        results = _pageable_courses(body, timeout=timeout)
        for r in results:
            if r['code'] == c:
                return r
        return None

    # Try the code as given
    found = _try_exact(target)
    if found:
        return found

    # If code lacks H/Y suffix, try common variants
    if not re.search(r'[HY]\d$', target):
        for suffix in ('H1', 'Y1', 'H5', 'H3', 'Y3'):
            found = _try_exact(target + suffix)
            if found:
                return found

    return None
