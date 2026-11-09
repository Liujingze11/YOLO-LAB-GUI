# Consolidate development on main

The user requested all current work be pushed, merged into `main`, and all other active repository branches removed. GUI and CLI remain independent repositories, both developed directly on `main`.

## GUI history and content

- Previous native workbench head: `437c1d99bda7e57599a95b0e672fecaaa4e743a0`.
- Previous legacy training `main`: `51f772c1e6c0bc2854fa7b4a79f8ab10aaa872f6`.
- These histories have no merge base. Preserve both as merge parents, using the current native workbench tree. Its model-development provenance already names the legacy training commit above.
- Include package migration, project-home and screening improvements, unified shortcuts, message boxes, title bar, tests and verification documentation.
- Keep personal software settings, runtime overlays, model weights and generated data outside the commit. The personal settings hash was checked before and after verification.
- Keep the existing version `1.5.2`; this consolidation does not publish a package or release.

## Clean-source verification

Exported the staged tree with `git checkout-index` into `/tmp/yolo-main-export-20261109`, excluding ignored local configuration. The existing interpreter and dependency overlay were reused; the source and user preferences were isolated.

The initial clean-source run exposed missing annotation shortcut entries without personal `software.yaml`, plus test assumptions about the local language. Fixed default bindings by capturing the generated UI defaults before preferences or page isolation can alter them. Existing user bindings retain priority. The integration fixture now uses independent minimal Chinese settings, and a fresh English-settings regression covers defaults, customization, reload and page isolation.

- New regression reproduced the missing `actionPolygon` entry before the fix.
- Shortcut integration: **9/9 passed**.
- Final clean-source suite: **251 tests passed, 48.087s**.
- Source distribution built successfully; category defaults, SAM2 YAML and new modules are included, while personal `software.yaml` and `.runtime/` are excluded.
- `git diff --cached --check` passed. No product-code changes follow these checks; the history merge preserves the tested tree.

```bash
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/yolo-main-export-mpl PYTHONPATH=/path/to/dependency-overlay:. python -m unittest discover -s tests -v
python setup.py sdist --dist-dir /tmp/yolo-main-package
```
