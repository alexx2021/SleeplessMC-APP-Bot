from pathlib import Path
import tempfile
import unittest

from config import ConfigurationError, load_config
from tests.common import environment


class ConfigTests(unittest.TestCase):
    def test_valid_configuration_and_numbered_questions(self):
        config = load_config(environment(), None)

        self.assertEqual(config.application_questions, ("First question?", "Second question?"))
        self.assertIn("1. First question?\n2. Second question?", config.application_prompt)
        self.assertEqual(config.bot_activity, "Applications for Example Server")

    def test_reports_all_missing_values(self):
        values = environment()
        del values["DISCORD_TOKEN"]
        del values["SERVER_IP"]

        with self.assertRaisesRegex(ConfigurationError, "DISCORD_TOKEN, SERVER_IP"):
            load_config(values, None)

    def test_rejects_malformed_ids_and_boolean(self):
        with self.assertRaisesRegex(ConfigurationError, "GUILD_ID"):
            load_config(environment(GUILD_ID="not-an-id"), None)
        with self.assertRaisesRegex(ConfigurationError, "ENABLE_JISHAKU"):
            load_config(environment(ENABLE_JISHAKU="sometimes"), None)

    def test_decodes_newlines_and_removes_blank_questions(self):
        for questions in ("One?\n\n Two? ", r"One?\n\n Two? "):
            with self.subTest(questions=repr(questions)):
                config = load_config(environment(APPLICATION_QUESTIONS=questions), None)
                self.assertEqual(config.application_questions, ("One?", "Two?"))

    def test_loads_double_quoted_newlines_from_dotenv(self):
        values = environment(APPLICATION_QUESTIONS="One?\\nTwo?")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, ".env")
            path.write_text(
                "\n".join(f'{name}="{value}"' for name, value in values.items()),
                encoding="utf-8",
            )
            config = load_config({}, path)
        self.assertEqual(config.application_questions, ("One?", "Two?"))

    def test_rejects_blank_and_oversized_questions(self):
        with self.assertRaisesRegex(ConfigurationError, "at least one"):
            load_config(environment(APPLICATION_QUESTIONS=" \\n "), None)
        with self.assertRaisesRegex(ConfigurationError, "2,000"):
            load_config(environment(APPLICATION_QUESTIONS="x" * 2_000), None)

    def test_environment_retargets_all_content_and_sheet_names(self):
        config = load_config(
            environment(
                SERVER_NAME="Another Community",
                SERVER_IP="other.example.test",
                APPLICATION_QUESTIONS="A custom question?",
                RULES_AGREEMENT_TEXT="Custom agreement.",
                WELCOME_DETAILS="Custom welcome details.",
                PAYMENT_UNIT="gem",
                BOT_ACTIVITY="Helping ${SERVER_NAME}",
                GOOGLE_SPREADSHEET_NAME="Other Book",
                BANNED_PLAYERS_WORKSHEET="Other Bans",
                PAYMENTS_WORKSHEET="Other Payments",
                DISCIPLINE_WORKSHEET="Other Discipline",
                FINANCES_WORKSHEET="Other Finances",
            ),
            None,
        )

        self.assertIn("Another Community", config.application_prompt)
        self.assertIn("other.example.test", config.welcome_message("@member"))
        self.assertIn("Custom welcome details.", config.welcome_message("@member"))
        self.assertEqual(config.application_questions, ("A custom question?",))
        self.assertIn("Custom agreement.", config.application_prompt)
        self.assertEqual(config.payment_unit, "gem")
        self.assertEqual(config.bot_activity, "Helping Another Community")
        self.assertEqual(
            (
                config.google_spreadsheet_name,
                config.banned_players_worksheet,
                config.payments_worksheet,
                config.discipline_worksheet,
                config.finances_worksheet,
            ),
            ("Other Book", "Other Bans", "Other Payments", "Other Discipline", "Other Finances"),
        )


if __name__ == "__main__":
    unittest.main()
