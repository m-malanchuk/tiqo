# tiqo icons — swap by editing SVG

Runtime loads **SVG masters** (rasterised to pixmaps in-process):

```
icons/
  source/
    app.svg         # colour mark — window / task-switcher / settings «Цветная»
    tray-dark.svg   # tray glyph on dark panels
    tray-light.svg  # tray glyph on light panels
```

## Replace a style

1. Edit the matching file under `source/`.
2. Restart the app (icons are cached per process).

Theme auto-picks `tray-dark` vs `tray-light`; settings may force dark / light / colour (`app.svg`).

## Window title-bar / task-manager (KDE)

Plasma resolves `Icon=tiqo` from the icon theme. On startup the app installs:

- `~/.local/share/icons/hicolor/scalable/apps/tiqo.svg`
- `~/.local/share/icons/hicolor/{16,22,24,32,48,64,128,256}x…/apps/tiqo.png`
- `~/.local/share/applications/tiqo.desktop` (`Icon=tiqo`)

Sized **PNG** copies avoid a blank/glitchy mark in the task manager (SVG-only was unreliable). Do not add a local `hicolor/index.theme` — it breaks the system hicolor directory list.
