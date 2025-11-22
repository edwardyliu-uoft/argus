"""Comprehensive tests for Argus MCP Server."""

import time
import pytest

from argus.services.mcp.server import (
    create_server,
    ArgusMCPServer,
    start,
    stop,
)


def test_create_server_returns_process():
    """`create_server` should return an `ArgusMCPServer` instance."""
    srv = create_server(port=0)
    assert isinstance(srv, ArgusMCPServer)


def test_create_server_with_custom_params():
    """Test creating server with custom parameters."""
    srv = create_server(
        port=9999,
        host="0.0.0.0",
        name="Test Server",
        mount_path="/test",
    )

    assert srv.port == 9999
    assert srv.host == "0.0.0.0"
    assert srv.name == "Test Server"
    assert srv.mount_path == "/test"


def test_start_and_stop_server_process():
    """Starting the server should spawn a child process which can be stopped."""
    srv = create_server(port=0)
    srv.start()

    # Give the child process a moment to start
    time.sleep(1.0)

    assert srv.is_alive(), "Server process should be alive after start()"
    assert srv.pid is not None, "Server process should have a pid"

    # Stop and join
    srv.stop()

    assert not srv.is_alive(), "Server process should not be alive after stop()"


def test_stop_non_running_server():
    """Stopping a non-running server should not raise an error."""
    srv = create_server(port=0)
    # Don't start it
    srv.stop()  # Should not raise


def test_stop_with_timeout():
    """Test stop with custom timeout."""
    srv = create_server(port=0)
    srv.start()
    time.sleep(1.0)

    assert srv.is_alive()
    srv.stop(timeout=1.0)
    assert not srv.is_alive()


def test_server_attributes():
    """Test that server has required attributes."""
    srv = create_server(
        port=8765,
        host="127.0.0.1",
        name="Attr Test",
        json_response=False,
        mount_path="/api",
    )

    assert srv.port == 8765
    assert srv.host == "127.0.0.1"
    assert srv.name == "Attr Test"
    assert srv.json_response is False
    assert srv.mount_path == "/api"
    assert srv.app is None  # Not started yet


def test_global_start_stop_functions():
    """Test the global start() and stop() functions."""
    # Start server
    srv = start(port=0)

    assert srv is not None
    assert isinstance(srv, ArgusMCPServer)
    time.sleep(1.0)
    assert srv.is_alive()

    # Stop server
    stop()
    time.sleep(0.5)
    assert not srv.is_alive()


def test_multiple_starts_stops():
    """Test starting and stopping server multiple times."""
    for _ in range(2):
        srv = create_server(port=0)
        srv.start()
        time.sleep(0.8)
        assert srv.is_alive()

        srv.stop()
        time.sleep(0.3)
        assert not srv.is_alive()


def test_server_process_name():
    """Test that server process has correct name."""
    srv = create_server(port=0)
    assert srv.name == "ArgusMCPServerProcess" or "Argus" in srv.name
