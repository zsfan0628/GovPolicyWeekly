# UI Preview 02

Shared Apple-inspired glass Qt Quick workspace with two entry points.
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

Version 02 replaces the dark sidebar with a floating glass navigation bar and a
light workspace. The glass fragment shader samples the generated landscape,
blurs and refracts it at the edges, and adds a directional rim highlight.
The selection lens uses a damped spring. This is a custom cross-platform visual
effect, not Apple's native Liquid Glass API. It does not sample the macOS desktop.
Glass is confined to navigation and transient menus to preserve text contrast.

The startup animation gathers text-mask particles into the application name and
crossfades into the workspace. It can be skipped and disabled with reduced motion.
Reduced transparency uses opaque surfaces; the software renderer selects that
fallback automatically. No background animation continues after startup.

Reference reviewed: [Rice-dog/code-codex](https://github.com/Rice-dog/code-codex),
commit `dbbc665b677624a26b98fdcd41f1db3f1a407bd2`, especially
`particle-image-startup.ts`, `startup-transition-player.ts`, and
`startup-transition.css`. Its source is MIT-licensed. The independent Qt
implementation borrows the ideas of particle assembly, an isolated startup layer,
and a fade handoff; it does not embed the project's code, inject into Codex, use
its plugin system, or copy its media assets. Any future source reuse must retain
the upstream copyright and license notice.

The shader is precompiled for Metal, HLSL and GLSL. To rebuild it using this
environment's Qt Shader Baker:

```sh
./.venv-release-check/lib/python3.13/site-packages/PySide6/qsb --qt6 --qsbversion 64 \
  -o ui/preview/shaders/glass.frag.qsb ui/preview/shaders/glass.frag
```

The independent preview is still offline. No new Windows installer is published
by this UI change, and Windows rendering has not yet been tested on a real PC.

## Wallpaper Asset

The current background is `ui/preview/assets/glacier-spiti.jpg`, selected by the
user from the glacier-texture reference. Photo by
[Sayan Dutta on Unsplash](https://unsplash.com/photos/a-large-glacier-with-ice-Atibs4SB4n4),
published November 3, 2022. The source describes the braided Spiti River. It is
available under the [Unsplash License](https://unsplash.com/license).
The image is bundled locally, so startup does not require a network connection.
A light overlay and viewport crop keep the glass controls legible; the source
image is not recolored. See `assets/ATTRIBUTION.md` for provenance.

Previous background, retained for comparison:
`ui/preview/assets/river-landscape.jpg`. Generated with the built-in
image generation tool, then JPEG-encoded for the preview. It is an illustrative
landscape, not a photograph or a claim about an actual location.

Final generation prompt:

> Create one photorealistic desktop wallpaper asset, wide 16:10 landscape
> composition, for a refined Chinese policy research desktop app. An aerial
> oblique view of a broad gently curving jade-green river beside lush green hills
> and patchwork agricultural fields, a far horizon of mist-free silver-gray
> mountain ridges under a pale bright overcast sky. Calm daylight, natural colors,
> crisp visible water and terrain details, restrained editorial landscape
> photography. River enters from lower left and curves toward upper right. Open
> pale silver sky fills upper 25 percent; do not put a mountain peak dead center.
> Palette balanced cool pale gray, sage green, turquoise water, a small amount of
> natural yellow-green farmland, no orange or purple. No people, buildings,
> signage, logos, text, panels, buttons, decorations, bokeh, or abstract orbs.
> This is a real-looking landscape wallpaper, not an interface screenshot,
> no dark overlay. Fine detail at high resolution.

Interactive checks and screenshots:

```sh
./.venv-release-check/bin/python ui_preview.py --smoke-test
```
