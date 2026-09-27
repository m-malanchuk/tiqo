# tiqo Plasma widget (`org.tiqo.work`)

Separate Plasma 6 plasmoid for the «В работе» roster. Talks to the running
tiqo app only over D-Bus (`org.tiqo.App` / `org.tiqo.App1`). See `docs/DBUS.md`.

## After every UI fix (required)

Plasma keeps **stale QML** and can leave **several applet instances** (panel +
desktop). Do **not** rely on `install-dev.sh` alone or on the “Add widgets”
browser after a fix.

```bash
bash plasma/reset-widget.sh
```

That script always:

1. Removes **all** `org.tiqo.work` instances (every panel + desktop)
2. Wipes **`~/.cache/plasmashell/qmlcache`** (full cache, not a tiqo-only glob)
3. Reinstalls the package from `plasma/org.tiqo.work`
4. Adds **one** fresh copy to the first panel

### Preview without restarting plasmashell

**Separate window** (full popup UI, not in the tray):

```bash
plasmawindowed org.tiqo.work
```

**Real system tray / Notification Area** (no panel, no shell restart):

```bash
bash plasma/preview-tray.sh
```

That runs `plasmawindowed --statusnotifier org.tiqo.work`: an icon appears
in the tray; LMB opens the same plasmoid popup. Stop with Ctrl+C.
Does **not** replace a stale *panel* applet — only a tray preview.

**Panel applet** (next to the tray): `bash plasma/reset-widget.sh`.
If the panel still shows old QML, that is in-memory cache inside
plasmashell — tray preview above is the way to dogfood without
`kquitapp6 plasmashell`.

tiqo must be running (`uv run tiqo` or `uv run tiqo-demo --run`) so
`busctl --user call org.tiqo.App /org/tiqo/App org.tiqo.App1 Ping` returns `pong`.

## Other scripts

| Script | Role |
|--------|------|
| `reset-widget.sh` | **Default after every plasmoid change** |
| `install-dev.sh` | Package files only (remove+install + kbuildsycoca); no instance scrub |
| `add-to-panel.sh` | Add one instance without the widget browser |

If the panel is still on an old UI after `reset-widget.sh`:

```bash
kquitapp6 plasmashell && kstart plasmashell
```

(restarts the shell UI, not the whole login session).

## Layout

- **Compact (panel):** chronometer + live clock of the primary running task.
- **Full (LMB popup):** `[n]` title, progress bar, clock, Start / Pause / Stop; header `В работе [N]`.
- Offline: «tiqo не запущен».

## Packaging

Same Arch package as the app will install this under
`/usr/share/plasma/plasmoids/org.tiqo.work/` (PKGBUILD stage).
