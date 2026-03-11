from django.test import TestCase


class CoreSmokeTest(TestCase):
    """Minimal smoke test so 'manage.py test core' runs at least one test."""

    def test_smoke(self):
        self.assertTrue(True)
