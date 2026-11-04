# Unified native workbench

User approved the discussed direction: one stable frame for screening, annotation
and development; neutral iOS-inspired materials; preserve all functions and state.
Implement in the current checkout, single agent, no commit or branch changes.

## Tasks

- [x] Add a shared title/project header around the existing page stack. Hide it
  on the project gallery. Keep the actual annotation canvas, actions, docks and
  page instances intact. Elide long names rather than widening the window.
- [x] Unify typography, control sizes, command surfaces and content insets.
  Keep glass on navigation/chrome and legible white/gray content panels.
  Compact screening paths into an elided source label with full path tooltip.
  Give the model tabs a segmented style and reduce duplicate page padding.
- [x] Add keyboard-accessible folding to training parameter cards, initially
  collapse augmentation, retaining values and splitter resizing. Verify page
  switches, homepage/project changes, folding, language, dark appearance and
  representative 1440×960 / 1100×760 captures with isolated configuration.

## Verification

Extend integration checks for stable header/content geometry and retained values.
Run `python -m unittest discover -s tests` in the existing isat_env with
`QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.runtime/python:$PWD"`.
Inspect new screenshots; never write user configuration or use real project data.
Existing canvas, import/save safety, shortcuts and training tests are regressions.

## Progress

Complete. Added a persistent training action bar after small-window inspection;
synchronized the existing model theme control across all three work pages.
The project gallery retains its light presentation and original heading sizes.
Card translation and the existing advanced-section animation were repaired as
part of preserving fold controls and their state.

159 tests passed in 35.034 seconds. Screenshot checks passed at 1440×960 and
1100×760, including page switching, temporary screening import, real polygons,
folding, six model tabs, dark mode, long names and language switching.
Code review performed locally under the repository's single-agent constraint.
Verification: `docs/superpowers/verification/2026-11-04-unified-workbench/`.
