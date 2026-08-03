"""Safety checks for the recovered local MySQL operator launcher."""

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimeLauncherTests(unittest.TestCase):
    def test_mysql_launcher_reuses_data_without_initializing_or_registering_a_service(self) -> None:
        launcher = (
            PROJECT_ROOT / "scripts" / "start-local-mysql.ps1"
        ).read_text(encoding="utf-8")

        for required in (
            "$env:LOCALAPPDATA",
            "mysql-data",
            "Test-Path -LiteralPath $systemDatabase -PathType Container",
            "--bind-address=127.0.0.1",
            "--mysqlx=OFF",
            "-WindowStyle Hidden",
            "Get-NetTCPConnection",
        ):
            self.assertIn(required, launcher)

        for unsafe in ("--initialize", "Remove-Item", "New-Service", "sc.exe"):
            self.assertNotIn(unsafe, launcher)


if __name__ == "__main__":
    unittest.main()
