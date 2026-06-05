import json
from pathlib import Path
import unittest


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "audit-row.schema.json"


class AuditRowSchemaTest(unittest.TestCase):
    def test_pending_model_is_required_boolean_field_not_row_status(self):
        schema = json.loads(SCHEMA_PATH.read_text())

        self.assertIn("pending_model", schema["required"])
        self.assertEqual(schema["properties"]["pending_model"], {"type": "boolean"})
        self.assertNotIn("pending_model", schema["properties"]["row_status"]["enum"])


if __name__ == "__main__":
    unittest.main()
