"""Government policy desktop app with the glass workspace and real collection engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main():
    if "--run-cli" in sys.argv:
        sys.argv.remove("--run-cli")
        from qt_app import run_cli_from_frozen
        run_cli_from_frozen()
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        from gov_report.self_test import run_self_test
        return run_self_test(Path(sys.argv[2]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--artifacts", type=Path, default=Path("release-check/desktop"))
    args = parser.parse_args()
    from gov_report.desktop import DesktopController
    from ui_preview import Sources, launch_workspace
    fixture = None
    if args.smoke_test:
        from scripts.test_desktop_app import DesktopFixture
        from gov_report.desktop import SettingsStore
        fixture = DesktopFixture(args.artifacts / "fixture")
    def factory():
        if fixture:
            sources = Sources(fixture.sources)
            store = SettingsStore(fixture.root / "settings.json", fixture.root / "no-legacy-settings")
            store.save(dict(openai_base_url=fixture.url + "/v1", openai_api_key=fixture.key,
                            use_llm=True, browser_fallback=False, output_root=str(fixture.root / "output"),
                            sleep_seconds=0, start_date="2026-10-18", end_date="2026-10-18"))
            return sources, DesktopController(sources, store, fixture.root)
        sources = Sources()
        return sources, DesktopController(sources)
    check = None
    if args.smoke_test:
        from scripts.test_desktop_app import run_checks
        check = lambda *values: run_checks(*values, fixture=fixture)
    try:
        return launch_workspace(factory, check, args.artifacts)
    finally:
        if fixture:
            fixture.close()


if __name__ == "__main__":
    raise SystemExit(main())
