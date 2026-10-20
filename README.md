# GovPolicyWeekly

**English** | [简体中文](README.zh-CN.md)

A desktop tool for collecting Chinese government policy and personnel announcements and producing weekly PDF reports with clickable source titles.

## Desktop Workspace

- Glass-style navigation, a bundled glacier background and an optional startup animation.
- Calendar date selection, highlighted 7-day / 30-day presets, and searchable selection across 30 configured sites.
- Real collection progress, filterable logs, stop controls and report history.
- OpenAI-compatible model discovery and selection, with an optional rule-based fallback.
- Attachment downloads and PDF export without a mandatory LibreOffice installation. Word, Excel and JSON exports are also retained.
- Locally saved preferences, masked API key input, reduced motion and reduced transparency.

The main workspace runs the real collection engine. `ui_preview.py` remains a separate, explicitly offline design demo.

## Windows Downloads

Download from [GitHub Releases](https://github.com/zsfan0628/GovPolicyWeekly/releases/latest):

- **Installer:** run `GovPolicyWeekly_Setup_*.exe`.
- **Portable:** fully extract `GovPolicyWeekly_windows_portable.zip`, then open `GovPolicyWeekly.exe`. Keep its supporting folders alongside it.

Windows 10/11, 64-bit. Packaged downloads do not require a separate Python or LibreOffice installation. The lean GitHub build uses an installed Microsoft Edge or Google Chrome for browser fallback.

**Source updates are not automatic application updates.** An existing release may contain an older interface. Check its release notes; the new workspace must pass a new Windows build before it is available as a downloadable executable.

## Run From Source

Use Python 3.10 or newer. The desktop UI requires PySide6 6.10 or newer within the 6.x series.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
python -m pip install -r requirements-windows-build.txt
python desktop_app.py
```

On macOS, create a local double-clickable desktop launcher:

```bash
python scripts/create_mac_preview_app.py --production
```

This launcher references the current project and Python environment; it is not a standalone macOS distribution. Keep both in place.

Legacy interfaces remain available as `qt_app.py` and `app.py` (the latter requires Tkinter). Launch the offline design demo with `python ui_preview.py`.

## Generate a Report

1. Choose a date range and one or more sites. Recent-date presets end yesterday.
2. Enter your model service's API base URL and API key, click the model-discovery button, and select a model. Or disable model classification to use the configured rules only.
3. Choose an output folder and collection options, then start generation.
4. Open the resulting PDF from the workspace or report history. Review warnings and source links before relying on a report.

Collection does not impose channel or detail-count limits. Large selections can take time. It follows discovered public navigation and pagination; this does not guarantee every page on a site is discoverable. Browser fallback helps with JavaScript pages and some access restrictions, but cannot guarantee access to every site.

Rules retain clear matches and reject clear non-target content. Ambiguous candidates are passed to the selected model. Without a model, ambiguous candidates are excluded unless rule fallback is explicitly enabled.

## Privacy and Local Settings

Bring your own model API credentials. Model requests are sent to the service you configure and may incur charges from that provider.

- API keys are masked in the UI and redacted from the new workspace's logs. Local settings are **not encrypted**.
- Settings use the user's application data directory: `~/Library/Application Support/GovPolicyWeekly/` on macOS, `%APPDATA%\GovPolicyWeekly\` on Windows, and the XDG configuration directory on Linux.
- On first use, the workspace can import a legacy `user_settings.json` from the application folder without modifying that file.
- Personal settings, environment files, reports, logs, caches, virtual environments and old development Git history are not part of the allowlisted source package.
- Do not upload local settings, credentials, personal paths or generated reports to a public issue or repository. Redact diagnostics before sharing them.

Maintainers should run `python scripts/prepare_github_source.py` before distributing source. Use `--upload-dir` with a **new destination path that does not already exist** to produce a checked browser-upload snapshot. The script checks known local credentials, common token formats and personal home paths, and stops on a match. These checks reduce risk; they cannot recognize every kind of private data.

## Command Line

```bash
python main.py --start-date 2026-10-01 --end-date 2026-10-07
```

For model configuration, set `GOV_REPORT_OPENAI_BASE_URL`, `GOV_REPORT_OPENAI_API_KEY` and `GOV_REPORT_OPENAI_MODEL` in your own environment. Never commit their real values. The command line also supports the legacy application-folder settings file; the new workspace passes its saved configuration directly to its worker.

Useful options include `--no-llm`, `--no-browser-fallback`, `--no-download-attachments` and `--allow-rule-fallback`. Run `python main.py --help` for the full list.

## Tests and Builds

```bash
python -m unittest discover -s tests -v
python desktop_app.py --self-test release-check/desktop-self-test.json
python desktop_app.py --smoke-test --artifacts release-check/desktop-integration
python ui_preview.py --smoke-test
```

The desktop integration test uses a local HTTP site and a local model-service fixture. It exercises the real worker, classification, attachment downloads, linked PDF export, persistence and stop controls without calling paid APIs or live government sites.

GitHub Actions can build and check the Windows executable, installer and portable archive. A version tag triggers release publication after checks pass; a manual workflow run produces test artifacts. See [Windows build instructions](WINDOWS_BUILD.md).

## Website Coverage and Credits

The latest documented site-navigation review covers 30 sites on **2026-10-18**, including public columns, pagination, buttons, dropdowns and search entry points. It does not certify all historical pages, authenticated services or form submissions. See the [site audit](docs/site-audit-2026-10-18.md) and [changelog](CHANGELOG.md). Sites may change after any test.

Icons: Lucide, ISC license. Wallpaper attribution and the Unsplash license are documented in [asset credits](ui/preview/assets/ATTRIBUTION.md). The glass effect is a custom cross-platform Qt implementation, not Apple's native Liquid Glass API; motion references are documented in [UI notes](ui/preview/README.md).
