import uuid

from django.test import SimpleTestCase as TestCase

from backend.utils.uuid_validation import validate_uuid


class ValidateUuidTests(TestCase):
    def test_accepts_canonical_uuid_string(self):
        value = str(uuid.uuid4())
        self.assertTrue(validate_uuid(value))

    def test_accepts_uppercase_uuid_string(self):
        value = str(uuid.uuid4()).upper()
        self.assertTrue(validate_uuid(value))

    def test_accepts_uuid_object(self):
        # Django's `<uuid:...>` path converter hands the view an already-parsed
        # uuid.UUID instance (e.g. the follow/block routes). Passing that object
        # straight through must not crash — it did, with AttributeError, which
        # surfaced as a 500 on every follow/block mutation.
        self.assertTrue(validate_uuid(uuid.uuid4()))

    def test_rejects_non_uuid_string(self):
        self.assertFalse(validate_uuid("not-a-uuid"))

    def test_rejects_empty_string(self):
        self.assertFalse(validate_uuid(""))

    def test_rejects_none(self):
        self.assertFalse(validate_uuid(None))
