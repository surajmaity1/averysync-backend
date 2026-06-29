from django.test import SimpleTestCase as TestCase

from backend.utils.env import env_bool


class EnvBoolTests(TestCase):
    def test_truthy_strings_parse_true(self):
        for raw in ["true", "True", "TRUE", "1", "yes", "on"]:
            with self.subTest(raw=raw):
                self.assertTrue(env_bool("FLAG", default=False, _getenv=lambda _: raw))

    def test_falsy_strings_parse_false(self):
        for raw in ["false", "False", "FALSE", "0", "no", "off", ""]:
            with self.subTest(raw=raw):
                self.assertFalse(env_bool("FLAG", default=True, _getenv=lambda _: raw))

    def test_missing_returns_default(self):
        self.assertTrue(env_bool("FLAG", default=True, _getenv=lambda _: None))
        self.assertFalse(env_bool("FLAG", default=False, _getenv=lambda _: None))
