# Contributing

Thanks for helping improve Invenux. Contributions should keep it portable, safe by default, and useful without a database service.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python -m compileall -q app.py core.py inspector.py reporting.py snapshots.py i18n.py paths.py build.py scripts tests
python build.py --console
```

Windows PowerShell uses `.venv\\Scripts\\Activate.ps1` for activation.

## Polling checks

`node --test tests/*.mjs` runs the interface checks (incremental table updates,
keyboard navigation of the table, the SSH form) using Node's standard library;
no `node_modules` are needed. To check scrolling in a browser,
run `python scripts/demo_server.py --machines 3000`, load the printed spreadsheet,
and start collection with fictional SSH credentials.

`GET /api/state` returns the complete state. `GET /api/state?since=<revision>`
returns changed records keyed by `ip`; merge them unless `reset` is true, in
which case replace the local records. Use the returned `revision` for the next
request. `more` means more changes remain, including after `scanning` becomes
false. Record batches target 120 KB before metadata; a single larger record is
sent whole. Missing or obsolete revisions return the full state. Analytics are
cached by revision, and snapshot history is refreshed after collection ends.

## Translations

The interface catalog is the JSON block `<script id="i18n-catalog">` in `ui/index.html`, one object per language (`pt-br`, `en`, `es`) with the same keys. Messages generated in Python live in `i18n.py`, and report labels in `reporting.py` (`COLUMN_LABELS`, `REPORT_TEXT`, `DETAIL_TEXT`, `TEMPLATE_TEXT`). Tests fail when a language misses a key or the interface uses a key that is not in the catalog. To add a language, add it to all four places and to `SUPPORTED_LANGUAGES` in `i18n.py`.

## Brand and README media

- `python scripts/render_brand.py` renders `brand/icon.svg` and `brand/icon-small.svg` into `brand/icons/`, `brand/invenux.ico` and `brand/invenux.icns`, plus the README wordmarks and `brand/social-preview.png`. It needs Google Chrome and Pillow.
- `node scripts/capture_media.mjs .venv/bin/python en pt-br es` starts `scripts/demo_server.py` (the real app with a fictional fleet on `192.0.2.0/24` and a fixed 10:42 clock) and writes the screenshots, demo GIFs and Excel overview to `docs/media/`. It needs Node 22+, Google Chrome, ffmpeg and LibreOffice.
- The social preview is uploaded by hand in the repository settings (Settings, General, Social preview).

## Guidelines

- Open an issue first for major product, architecture, or compatibility changes.
- Keep the GUI, inventory orchestration, SSH collector, and report rendering in separate layers.
- Add tests when changing input handling, host status semantics, report formats, or security-sensitive behavior.
- Keep examples anonymized: use documentation addresses (`192.0.2.0/24`) and invented names. Never commit credentials, customer hostnames/IP ranges, output reports, private logs, or local configuration.
- Document security trade-offs and keep strict verification as the default.
- Do not add a database or vendor connector unless it is optional and the user benefit is clear.

## Pull requests

Describe the problem and intended behavior, tests run, operating systems tested, and known limitations. Avoid combining large refactors with unrelated styling changes.
