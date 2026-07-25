"""D-Bus org.tiqo.App1 contract (interface name, Ping/Version, ListWork)."""

from __future__ import annotations

import json

import pytest
from app.api.dbus_service import (
    API_VERSION,
    INTERFACE,
    OBJECT_PATH,
    SERVICE_NAME,
    register_tiqo_dbus,
)
from app.api.session_facade import SessionFacade
from app.domain.models import LIST_FAVORITES_ID, TaskKind, TimerMode
from app.storage.task_repo import TaskRepo
from PySide6.QtCore import QCoreApplication
from PySide6.QtDBus import QDBusConnection, QDBusInterface

from tests.support.db import make_db


@pytest.fixture
def qapp() -> QCoreApplication:
    existing = QCoreApplication.instance()
    if existing is not None:
        return existing
    return QCoreApplication([])


@pytest.fixture
def dbus_session(qapp: QCoreApplication):
    """Register a temporary org.tiqo.App; skip if the bus or name is unavailable."""
    _ = qapp
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        pytest.skip("session bus unavailable")

    # Avoid colliding with a running tiqo instance.
    if bus.interface().isServiceRegistered(SERVICE_NAME).value():
        pytest.skip(f"{SERVICE_NAME} already owned (tiqo running?)")

    conn = make_db()
    facade = SessionFacade(conn)
    shown: list[bool] = []
    api = register_tiqo_dbus(facade, on_show_window=lambda: shown.append(True), parent=qapp)
    if api is None:
        pytest.skip("failed to register D-Bus service")

    yield {"api": api, "facade": facade, "conn": conn, "shown": shown, "bus": bus}

    bus.unregisterService(SERVICE_NAME)
    bus.unregisterObject(OBJECT_PATH)
    conn.close()


def test_interface_is_org_tiqo_app1(dbus_session: dict) -> None:
    bus = dbus_session["bus"]
    intro = QDBusInterface(
        SERVICE_NAME,
        OBJECT_PATH,
        "org.freedesktop.DBus.Introspectable",
        bus,
    )
    reply = intro.call("Introspect")
    assert not reply.errorName(), reply.errorMessage()
    xml = reply.arguments()[0]
    assert f'interface name="{INTERFACE}"' in xml
    assert "local.TiqoDBusAdaptor" not in xml
    assert "Ping" in xml
    assert "Version" in xml
    assert "ListWork" in xml
    assert "ToggleChecklist" in xml
    assert "CompleteChecklist" in xml
    assert "WorkChanged" in xml


def test_ping_version_list_work(dbus_session: dict) -> None:
    bus = dbus_session["bus"]
    iface = QDBusInterface(SERVICE_NAME, OBJECT_PATH, INTERFACE, bus)
    assert iface.isValid(), iface.lastError().message()

    ping = iface.call("Ping")
    assert ping.arguments() == ["pong"]

    ver = iface.call("Version")
    assert ver.arguments() == [API_VERSION]

    empty = iface.call("ListWork")
    assert json.loads(empty.arguments()[0]) == []

    task = TaskRepo(dbus_session["conn"]).create(
        LIST_FAVORITES_ID,
        "Focus",
        default_mode=TimerMode.STOPWATCH,
    )
    dbus_session["facade"].engine.start(task.id, use_task_default=True)
    rows = json.loads(iface.call("ListWork").arguments()[0])
    assert len(rows) == 1
    assert rows[0]["task_id"] == task.id
    assert rows[0]["state"] == "running"
    assert rows[0]["can_pause"] is True


def test_show_window_callback(dbus_session: dict) -> None:
    bus = dbus_session["bus"]
    iface = QDBusInterface(SERVICE_NAME, OBJECT_PATH, INTERFACE, bus)
    iface.call("ShowWindow")
    assert dbus_session["shown"] == [True]


def test_toggle_checklist_round_trip(dbus_session: dict) -> None:
    bus = dbus_session["bus"]
    iface = QDBusInterface(SERVICE_NAME, OBJECT_PATH, INTERFACE, bus)
    task = TaskRepo(dbus_session["conn"]).create(
        LIST_FAVORITES_ID,
        "Checklist",
        kind=TaskKind.CHECKLIST,
        is_favorite=True,
    )
    result = iface.call("ToggleChecklist", task.id)
    assert result.arguments() == ["ok"]
    row = dbus_session["facade"].list_tasks(LIST_FAVORITES_ID)
    snapshot = next(item for item in row if item.task_id == task.id)
    assert snapshot.is_completed is True
    assert snapshot.progress == 1.0
