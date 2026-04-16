import graphene
from graphene_django import DjangoObjectType
from django.conf import settings
from django.db.models import Q
from .models import Course
from .catalog import fetch_timetable_course_by_code, search_timetable_courses


class CourseType(DjangoObjectType):
    class Meta:
        model = Course
        fields = ('id', 'code', 'name', 'description', 'prerequisites')

    prerequisites = graphene.List(lambda: CourseType)

    def resolve_prerequisites(self, info):
        return self.prerequisites.all()


def _prefetch_course(code):
    return (
        Course.objects
        .prefetch_related(
            'prerequisites',
            'prerequisites__prerequisites',
            'prerequisites__prerequisites__prerequisites',
        )
        .get(code=code)
    )


def _sync_prerequisites(course, known_codes=None, depth=0, max_depth=3):
    """
    Wire prerequisite courses onto `course`, fetching from EASI any that
    are not yet in the DB.  Recurses up to max_depth levels.

    known_codes — pass when the caller already has the prerequisite code list
                  (avoids a redundant API round-trip for the parent course).
    """
    if not settings.UOFT_TIMETABLE_FALLBACK_ENABLED:
        return

    if known_codes is None:
        remote = fetch_timetable_course_by_code(
            code=course.code,
            session=settings.UOFT_TIMETABLE_SESSION,
            timeout=settings.UOFT_TIMETABLE_TIMEOUT_SECONDS,
        )
        if not remote:
            return
        prereq_codes = remote.get('prerequisite_codes') or []
    else:
        prereq_codes = known_codes

    for prereq_code in prereq_codes:
        try:
            prereq = Course.objects.get(code=prereq_code)
        except Course.DoesNotExist:
            if depth >= max_depth:
                continue
            remote_prereq = fetch_timetable_course_by_code(
                code=prereq_code,
                session=settings.UOFT_TIMETABLE_SESSION,
                timeout=settings.UOFT_TIMETABLE_TIMEOUT_SECONDS,
            )
            if not remote_prereq:
                continue
            prereq, created = Course.objects.get_or_create(
                code=remote_prereq['code'],
                defaults={
                    'name': remote_prereq['name'],
                    'description': remote_prereq['description'],
                },
            )
            if created:
                _sync_prerequisites(prereq, known_codes=remote_prereq.get('prerequisite_codes'), depth=depth + 1, max_depth=max_depth)
        course.prerequisites.add(prereq)


def _save_remote_course(remote):
    course, created = Course.objects.get_or_create(
        code=remote['code'],
        defaults={
            'name': remote['name'],
            'description': remote['description'],
        },
    )
    if created:
        _sync_prerequisites(course, known_codes=remote.get('prerequisite_codes'))
    return _prefetch_course(course.code)


class Query(graphene.ObjectType):
    course = graphene.Field(
        CourseType,
        code=graphene.String(required=True),
    )
    courses = graphene.List(
        CourseType,
        search=graphene.String(default_value=''),
    )

    def resolve_course(self, info, code):
        try:
            course = _prefetch_course(code)
            # Re-sync if course is cached but has no prerequisites wired yet.
            if not course.prerequisites.exists() and settings.UOFT_TIMETABLE_FALLBACK_ENABLED:
                _sync_prerequisites(course)
                return _prefetch_course(code)
            return course
        except Course.DoesNotExist:
            if not settings.UOFT_TIMETABLE_FALLBACK_ENABLED:
                return None
            remote = fetch_timetable_course_by_code(
                code=code,
                session=settings.UOFT_TIMETABLE_SESSION,
                timeout=settings.UOFT_TIMETABLE_TIMEOUT_SECONDS,
            )
            if not remote:
                return None
            return _save_remote_course(remote)

    def resolve_courses(self, info, search=''):
        q = (search or '').strip()
        qs = Course.objects.prefetch_related('prerequisites')

        if not q:
            return qs[: settings.SEARCH_RESULTS_LIMIT]

        local_results = list(
            qs.filter(Q(code__icontains=q) | Q(name__icontains=q))[: settings.SEARCH_RESULTS_LIMIT]
        )

        if (
            len(local_results) >= settings.SEARCH_RESULTS_LIMIT
            or not settings.UOFT_TIMETABLE_FALLBACK_ENABLED
        ):
            return local_results

        seen_codes = {course.code for course in local_results}
        remote_results = search_timetable_courses(
            query=q,
            session=settings.UOFT_TIMETABLE_SESSION,
            timeout=settings.UOFT_TIMETABLE_TIMEOUT_SECONDS,
            limit=settings.SEARCH_RESULTS_LIMIT,
        )

        merged = list(local_results)
        for remote in remote_results:
            if remote['code'] in seen_codes:
                continue
            merged.append(
                Course(
                    code=remote['code'],
                    name=remote['name'],
                    description=remote['description'],
                )
            )
            if len(merged) >= settings.SEARCH_RESULTS_LIMIT:
                break

        return merged


schema = graphene.Schema(query=Query)
