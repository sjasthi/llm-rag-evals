"""Static regression checks for high-impact browser rendering mistakes."""

from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FrontendRegressionTests(unittest.TestCase):
    def test_app_does_not_treat_html_tag_selectors_as_new_elements(self) -> None:
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        selector_used_as_constructor = re.compile(
            r'\$\("(?:article|button|div|p|small|span|strong)"\)\s*\.(?:addClass|text)'
        )

        self.assertIsNone(
            selector_used_as_constructor.search(javascript),
            "Use $('<tag>') to create an element; $('tag') selects and can move the existing page DOM.",
        )


if __name__ == "__main__":
    unittest.main()

