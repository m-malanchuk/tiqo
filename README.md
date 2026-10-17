# tiqo

Native personal time tracker for **Arch Linux, KDE Plasma 6, and Wayland**.

tiqo tracks what you are working on and how long it takes. It supports multiple
independent active tasks without turning time tracking into a habit or productivity
scoring system. All data stays in a local SQLite database.

## Features

- Stopwatch, countdown, and binary checklist tasks
- Nested tasks with safe parent/child session rules
- Multiple concurrent sessions for independent tasks
- Recurring tasks and explicit calendar assignments
- Editable completion history with filters, sorting, and CSV export
- System tray, autostart, notifications, and a Plasma 6 widget
- Local storage only: no account, cloud service, or network dependency

## Install

From a cloned checkout, build and install the Arch package with one command:

```bash
./packaging/build-package.sh
```

Run the script as a regular user. It uses `sudo` only to install required Arch
packages and the finished package. The application and `org.tiqo.work` Plasma
widget are installed together.

Launch `tiqo` from the application menu or from a terminal:

```bash
tiqo
```

## Development

Python 3.12 and [uv](https://docs.astral.sh/uv/) are used for the development
environment:

```bash
uv sync
uv run tiqo-demo --run
```

`tiqo-demo` recreates a showcase database with representative tasks, sessions,
recurrence rules, and history. It never uses the personal database.

Run the application with personal data using:

```bash
uv run tiqo
```

## Data

- Personal database: `~/.local/share/tiqo/tiqo.db`
- Showcase database: `~/.local/share/tiqo/demo.db`
- Configuration: `~/.config/tiqo/`
- Optional sounds: `~/.local/share/tiqo/sounds/`

Database files are intentionally excluded from Git. The showcase database is
generated locally from version-controlled seed code.

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run pyright
```

## Documentation

- [Design and data model](docs/DISDOC.md)
- [Architecture and code health](docs/CODE_AUDIT.md)
- [D-Bus API](docs/DBUS.md)
- [Roadmap and completion criteria](docs/TASKS.md)
- [Plasma widget development](plasma/README.md)

## Status

The application feature set is complete for the initial release. Final Arch
package and clean-install verification are the remaining release steps.
