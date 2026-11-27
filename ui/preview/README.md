# Desktop Workspace

Shared pearl-gray and dusty-rose Qt Quick workspace with two entry points.
`desktop_app.py` uses the real collection engine through `gov_report/desktop.py`.
`ui_preview.py` remains an independent offline preview and never calls the collection engine
or a model API, never reads `user_settings.json`, and never generates fake reports.
The 30 source names come from the local source configuration. Existing local PDF
files can be opened from the report page.

Run from the project directory:

```sh
./.venv-release-check/bin/python ui_preview.py
```

Use a Python environment with PySide6 >=6.10,<7 (including Qt Quick, QML and
QtSvg) and PyYAML. The PyInstaller specification now targets `desktop_app.py`
and includes the required Qt Quick modules and local UI assets. A new Windows
installer still requires a Windows build and verification.

On this Mac, `scripts/create_mac_preview_app.py` creates a double-clickable
`政策周报预览.app` on the desktop without opening a terminal. This is a local
launcher, not a self-contained distribution: it references the current project
directory and the Python environment used to create it. Keep both in place.
Launcher diagnostics are in `~/Library/Logs/GovPolicyWeekly/preview.log`.
Pass `--production` to create the functional `政策周报.app` instead. Existing
launchers are never overwritten. Both are local launchers, not standalone bundles.

## Real Engine

Run `python desktop_app.py` for real crawling, authenticated model discovery,
configuration persistence, live structured progress, attachment download, PDF
generation and report history. Settings are stored in the user's application
data directory, with one-time import from the legacy project settings. API keys
are masked in the UI and redacted from logs, but the local settings file itself
is not encrypted. Credentials are passed to the worker through its environment,
not command arguments or generated site files.

The worker runs outside the GUI process and can be stopped along with its browser
children. A running task requires confirmation before closing. Report success is
shown only after the worker exits successfully and its reported PDF exists.
`python desktop_app.py --smoke-test` exercises the real worker and exporters
against local HTTP/model fixtures without calling external APIs or websites.

The icon SVGs are from [Lucide](https://github.com/lucide-icons/lucide), licensed
under ISC. See `icons/LICENSE`.

## Appearance and Motion

The desktop app has a single palette and horizontal navigation. The month calendar highlights the selected range and displays its inclusive day count. Browsing into another selected month does not change the range. The configuration drawers reuse the real model and collection settings. During collection the calendar gives way to the live inspector; task recovery remains available afterwards.

The silent 4.8-second opening emits particles from one fixed point. Each landing deposits
a piece of “Welcome to Policy Weekly” on an ink background. The animation then
turns samples of the same letters into a luminous spiral, and settles the Chinese
wordmark onto the live navigation label. Settled strokes are drawn at 4x resolution from their first appearance, independently of the lower-resolution particle glow. The dark cinematic palette is confined to the opening.
Generate the assets offline with `python -m scripts.build_cinematic_intro`; the desktop
does not draw individual particles each frame. Site management keeps its interactive map.
The intro never reads task dates. Replay from Settings; click Skip or
press Escape for immediate entry.
Reduced motion bypasses the timeline. The GUI event loop also dismisses a
stalled intro 600 ms beyond the planned duration, independently of the animation frame clock.
Reduced transparency uses opaque surfaces; the software renderer selects that
fallback automatically. No background animation continues after startup.

Run `python -m scripts.preview_map_intro` to capture native Qt frames in
`release-check/world-mark/frames` and verify date independence, navigation
handoff and stalled-intro recovery. On macOS, run once with the normal
Metal renderer as well as the offscreen software renderer.

The shader is precompiled for Metal, HLSL and GLSL. To rebuild it using this
environment's Qt Shader Baker:

```sh
./.venv-release-check/lib/python3.13/site-packages/PySide6/qsb --qt6 --qsbversion 64 \
  -o ui/preview/shaders/glass.frag.qsb ui/preview/shaders/glass.frag
```

The independent preview is still offline. No new Windows installer is published
by this UI change, and Windows rendering has not yet been tested on a real PC.

Interactive checks and screenshots:

```sh
./.venv-release-check/bin/python ui_preview.py --smoke-test
```
