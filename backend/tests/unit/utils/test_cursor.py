import uuid
from datetime import datetime, timezone

from django.test import SimpleTestCase

from backend.utils.cursor import InvalidCursorError, decode_cursor, encode_cursor


class CursorTests(SimpleTestCase):
    def test_round_trips_created_at_and_id(self):
        created_at = datetime(2026, 7, 13, 10, 0, 0, tzinfo=timezone.utc)
        row_id = uuid.uuid4()

        cursor = encode_cursor(created_at, row_id)
        decoded_at, decoded_id = decode_cursor(cursor)

        self.assertEqual(decoded_at, created_at)
        self.assertEqual(decoded_id, row_id)

    def test_encoded_cursor_is_opaque(self):
        cursor = encode_cursor(datetime(2026, 7, 13, tzinfo=timezone.utc), uuid.uuid4())

        self.assertNotIn("|", cursor)
        self.assertNotIn(":", cursor)

    def test_malformed_cursor_raises(self):
        for bad in ["not-base64!!", "", "Zm9v"]:
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidCursorError):
                    decode_cursor(bad)
