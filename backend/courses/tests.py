from unittest.mock import patch

from django.test import TestCase, override_settings

from .models import Course
from .schema import Query


class CourseSearchTests(TestCase):
	def setUp(self):
		Course.objects.create(code='CSC108H1', name='Intro to Programming')
		Course.objects.create(code='MAT137Y1', name='Calculus with Proofs')

	@override_settings(UOFT_TIMETABLE_FALLBACK_ENABLED=False)
	def test_resolve_courses_searches_by_code_and_name(self):
		query = Query()

		by_code = query.resolve_courses(info=None, search='CSC')
		by_name = query.resolve_courses(info=None, search='Calculus')

		self.assertEqual([c.code for c in by_code], ['CSC108H1'])
		self.assertEqual([c.code for c in by_name], ['MAT137Y1'])

	@override_settings(
		UOFT_TIMETABLE_FALLBACK_ENABLED=True,
		SEARCH_RESULTS_LIMIT=25,
		UOFT_TIMETABLE_SESSION='20249',
		UOFT_TIMETABLE_TIMEOUT_SECONDS=1,
	)
	@patch('courses.schema.search_timetable_courses')
	def test_resolve_courses_merges_remote_when_local_insufficient(self, mock_search_remote):
		mock_search_remote.return_value = [
			{'code': 'CSC148H1', 'name': 'Intro to CS', 'description': ''},
			{'code': 'CSC108H1', 'name': 'Intro to Programming', 'description': ''},
		]

		query = Query()
		results = query.resolve_courses(info=None, search='CSC')

		self.assertEqual([c.code for c in results], ['CSC108H1', 'CSC148H1'])
		mock_search_remote.assert_called_once()

	@override_settings(
		UOFT_TIMETABLE_FALLBACK_ENABLED=True,
		UOFT_TIMETABLE_SESSION='20249',
		UOFT_TIMETABLE_TIMEOUT_SECONDS=1,
	)
	@patch('courses.schema.fetch_timetable_course_by_code')
	def test_resolve_course_falls_back_to_remote(self, mock_fetch_remote):
		mock_fetch_remote.return_value = {
			'code': 'PHY131H1',
			'name': 'Introduction to Physics I',
			'description': 'Mechanics and waves.',
		}

		query = Query()
		result = query.resolve_course(info=None, code='PHY131H1')

		self.assertIsNotNone(result)
		self.assertEqual(result.code, 'PHY131H1')
		self.assertEqual(result.name, 'Introduction to Physics I')
		mock_fetch_remote.assert_called_once()
