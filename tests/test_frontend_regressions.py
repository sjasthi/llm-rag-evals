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

    def test_experiments_explain_layers_and_score_contracts(self) -> None:
        javascript = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        for phrase in (
            "Baseline diagnostics",
            "Advanced evaluators",
            "Human review",
            "Operations",
            "What this score means",
            "No threshold; inspect the value directly.",
        ):
            self.assertIn(phrase, javascript)

    def test_frontend_does_not_combine_unlike_metrics(self) -> None:
        frontend = "\n".join(
            (PROJECT_ROOT / path).read_text(encoding="utf-8")
            for path in ("assets/js/app.js", "index.php", "api/evaluations.php")
        ).lower()
        self.assertNotIn("descriptive_average", frontend)
        self.assertNotIn("overall metric average", frontend)
        self.assertIn("do not combine unlike scores", frontend)


if __name__ == "__main__":
    unittest.main()
