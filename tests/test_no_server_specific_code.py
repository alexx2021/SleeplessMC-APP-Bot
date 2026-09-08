from pathlib import Path
import unittest


class ServerSpecificCodeTests(unittest.TestCase):
    def test_old_server_values_only_exist_in_environment_example(self):
        roots = [Path("main.py"), Path("config.py"), Path("utils.py"), *Path("cogs").glob("*.py")]
        source = "\n".join(path.read_text(encoding="utf-8") for path in roots)
        forbidden = (
            "Sleep" + "less",
            "play." + "sleep" + "less.community",
            "alexx" + "wastakenlol",
            "S" + "MC",
            "SD" + " Payments",
        )
        self.assertEqual([value for value in forbidden if value in source], [])


if __name__ == "__main__":
    unittest.main()
