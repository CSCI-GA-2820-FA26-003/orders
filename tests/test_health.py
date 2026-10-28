"""Health endpoint contract."""
from unittest import TestCase
from unittest.mock import patch

from wsgi import app
from service.models import db


class TestHealth(TestCase):
    """Check liveness independently of database availability."""

    def test_health(self):
        """It should return the exact JSON response without querying the database."""
        with app.test_client() as client:
            with patch.object(db.session, "execute", side_effect=AssertionError("Unexpected database query")):
                response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.get_json(), {"status": "OK"})
