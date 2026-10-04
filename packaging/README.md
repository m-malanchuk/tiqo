# Arch desktop integration

The package installs:

- `tiqo.desktop` into `/usr/share/applications/`;
- the autostart template into `/usr/share/tiqo/`;
- `source/app.svg` as the `tiqo` application icon in
  `/usr/share/icons/hicolor/scalable/apps/`;
- `plasma/org.tiqo.work/` into
  `/usr/share/plasma/plasmoids/org.tiqo.work/`.

The autostart entry is KDE-only and hidden from application menus. It is
opt-in: enable it in Settings, which copies the template to
`~/.config/autostart/tiqo.desktop`; disabling the setting removes that
user-level entry. Closing the window still follows the application setting and
normally leaves tiqo in the tray.

## Build and install from the current checkout

Run this as a normal user (not with `sudo`):

```bash
./packaging/build-package.sh
```

The script requires a clean tracked working tree, installs missing Arch
dependencies through `sudo`, creates a source archive from the current Git
commit, builds the package with `makepkg`, installs it, and removes the
temporary source archive.

For development, use `bash plasma/reset-widget.sh`; it installs the same
plasmoid content into the user Plasma package prefix and resets stale instances
and QML caches.
