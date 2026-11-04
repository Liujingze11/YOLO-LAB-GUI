# Native workbench unification — 2026-11-04

## Result

The existing page stack now sits in a common title/project frame. Screening,
annotation and model development share typography, neutral control materials,
spacing and light/dark appearance. Long names elide without widening the window.
The project gallery retains its original presentation.

Screening paths appear as a compact source name with a complete path tooltip.
Annotation retains its actual canvas, menus, actions and dock layout. Model
development uses segmented tabs, folding training groups and a fixed action bar
so Start/Stop remain visible while scrolling. Folding retains parameter values.
The existing advanced-section animation now owns its animation object, and
folding controls follow language changes.

## Evidence

- `tests.log`: 159 tests passed in 35.034 seconds.
- `ui.log`: native QWidget captures and interaction checks passed.
- `red.log`, `refinement-red.log`, `language-red.log`: checks reproduced missing
  shared header/folding, inaccessible small-window actions, isolated theme and
  untranslated folding titles before implementation.
- `screening.png`, `annotation.png`, `development.png`: primary work pages.
- `*-small.png`: 1100×760 layout; normal captures are 1440×960.
- `*-dark.png`: all three work pages use a consistent dark palette.
- `augmentation-expanded.png`: original augmentation controls remain available.
- `infer.png`, `export.png`, `logs.png`, `tools.png`, `settings.png`: model pages.
- `home.png`, `home-after-dark.png`, `long-project.png`, `english.png`,
  `development-english-small.png`: gallery, long names and translated controls.

Run from the repository root:

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.runtime/python:$PWD" \
  /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests
QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.runtime/python:$PWD" \
  /home/ljz/miniconda3/envs/isat_env/bin/python \
  docs/superpowers/verification/2026-11-04-unified-workbench/verify_ui.py
```

All projects and configuration used in verification were temporary. Original
`ISAT/software.yaml` SHA256 remained
`a538c2368fe057a70b13bb61b709bf0cd94ce31f6a0b3dca39a9179ee7ba7fa0`.
Materials use native Qt translucent surfaces; image pixels are not blurred.
Review was performed locally without subagents, commits or branch changes.
