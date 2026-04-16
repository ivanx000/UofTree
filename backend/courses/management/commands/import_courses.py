"""
Management command: import_courses
===================================
Bulk-imports UofT courses from the timetable API into the local database,
then wires up prerequisite relationships by parsing the free-text prerequisite
field that the API returns for each course.

Usage
-----
    python manage.py import_courses            # imports using settings defaults
    python manage.py import_courses --session 20249
    python manage.py import_courses --depts CSC MAT ECE PHY
    python manage.py import_courses --no-prereqs  # skip prerequisite wiring

How it works
------------
1. For every department prefix in DEPT_PREFIXES (or --depts), query the
   UofT timetable API once and collect all matching courses.
2. First pass: upsert each course (create if new, skip if already present).
3. Second pass: for each course whose API payload had a prerequisite field,
   extract all course codes from the text (e.g. "CSC148H1 or CSC150H1")
   and add them as prerequisite relationships if both courses exist locally.

Notes
-----
• The timetable API only lists courses *offered in the given session*.
  Some courses that exist in the calendar may not appear.
• Prerequisite parsing is regex-based and best-effort; non-standard phrasings
  may be missed.
• Running the command again is idempotent: existing records are not modified,
  existing prerequisite links are not duplicated.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from courses.catalog import fetch_timetable_courses_by_prefix
from courses.models import Course

# Complete list of Arts & Science + Engineering department codes at UofT.
# Add more as needed; each prefix triggers one API request.
DEPT_PREFIXES = [
    'ANT', 'ARC', 'AST',
    'BIO', 'BME', 'BOT',
    'CAN', 'CHE', 'CHM', 'CHN', 'CIN', 'CLA', 'COG', 'CSC', 'CWA',
    'DRM',
    'ECE', 'ECO', 'EEB', 'ENG', 'ENV', 'ESS', 'ETH',
    'FAH', 'FOR', 'FRE',
    'GER', 'GGR', 'GPH', 'GRK',
    'HIN', 'HIS', 'HMB', 'HPS',
    'INI', 'INS', 'ITA',
    'JAP', 'JPO',
    'KOR',
    'LAT', 'LIN',
    'MAT', 'MBP', 'MGT', 'MGY', 'MHI', 'MIE', 'MMG', 'MSE', 'MUS',
    'NFS', 'NMC',
    'PCL', 'PHL', 'PHY', 'PMA', 'POL', 'PRT', 'PSL', 'PSY',
    'REN', 'RLG', 'RSM',
    'SCI', 'SLA', 'SMC', 'SOC', 'SPA', 'STA', 'SWC',
    'TRN',
    'VIC', 'VIS',
    'WDW', 'WGS',
]


class Command(BaseCommand):
    help = (
        'Bulk-import UofT courses from the timetable API and wire up '
        'prerequisite relationships.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--session',
            default=None,
            help='Timetable session code (e.g. 20249). Defaults to settings.UOFT_TIMETABLE_SESSION.',
        )
        parser.add_argument(
            '--depts',
            nargs='+',
            default=None,
            metavar='PREFIX',
            help='Department prefix(es) to fetch (e.g. CSC MAT). Defaults to the full list.',
        )
        parser.add_argument(
            '--no-prereqs',
            action='store_true',
            default=False,
            help='Skip the prerequisite-wiring pass.',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=10,
            help='HTTP timeout per API request in seconds (default: 10).',
        )

    def handle(self, *args, **options):
        session = options['session'] or settings.UOFT_TIMETABLE_SESSION
        timeout = options['timeout']
        prefixes = [p.upper() for p in (options['depts'] or DEPT_PREFIXES)]
        wire_prereqs = not options['no_prereqs']

        self.stdout.write(
            f'Importing courses for session {session} '
            f'({len(prefixes)} department prefix(es))...\n'
        )

        # ── Pass 1: collect raw payloads ──────────────────────────────────────
        raw_payloads: dict[str, dict] = {}
        for prefix in prefixes:
            try:
                payload_map = fetch_timetable_courses_by_prefix(prefix, session, timeout=timeout)
                raw_payloads.update(payload_map)
                self.stdout.write(f'  {prefix}: {len(payload_map)} course(s)')
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(f'  {prefix}: fetch failed — {exc}')
                )

        self.stdout.write(f'\nTotal courses fetched: {len(raw_payloads)}\n')

        if not raw_payloads:
            self.stdout.write(self.style.WARNING('No courses fetched. Is the API reachable?'))
            return

        # ── Pass 2: upsert courses ────────────────────────────────────────────
        # fetch_timetable_courses_by_prefix already returns normalised dicts.
        normalized_map: dict[str, dict] = {}
        created_count = 0
        skipped_count = 0

        for code, normalized in raw_payloads.items():
            if not normalized:
                continue
            normalized_map[normalized['code']] = normalized

            _, created = Course.objects.get_or_create(
                code=normalized['code'],
                defaults={
                    'name': normalized['name'],
                    'description': normalized['description'],
                },
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            f'Courses created: {created_count}  |  already existed: {skipped_count}\n'
        )

        if not wire_prereqs:
            self.stdout.write(self.style.SUCCESS('Done (prerequisite wiring skipped).'))
            return

        # ── Pass 3: wire prerequisites ────────────────────────────────────────
        self.stdout.write('Wiring prerequisite relationships...')
        wired_count = 0
        missing_count = 0

        for norm_code, normalized in normalized_map.items():
            prereq_codes = normalized.get('prerequisite_codes') or []
            if not prereq_codes:
                continue

            try:
                course = Course.objects.get(code=norm_code)
            except Course.DoesNotExist:
                continue

            for prereq_code in prereq_codes:
                try:
                    prereq = Course.objects.get(code=prereq_code)
                    course.prerequisites.add(prereq)
                    wired_count += 1
                except Course.DoesNotExist:
                    missing_count += 1

        self.stdout.write(
            f'Prerequisite links added: {wired_count}  |  '
            f'prereq codes not in DB: {missing_count}\n'
        )
        self.stdout.write(self.style.SUCCESS('Done!'))
