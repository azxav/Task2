import socket

import pytest


def test_offline_guard_rejects_external_connect_before_network(monkeypatch):
    from doc_tasks.network import install_local_network_guard
    attempted = []
    monkeypatch.setattr(socket.socket, "connect", lambda self, address: attempted.append(address))
    original = socket.socket.connect
    try:
        install_local_network_guard()
        connection = socket.socket()
        with pytest.raises(OSError, match="Local-only"):
            connection.connect(("203.0.113.1", 443))
        connection.connect(("127.0.0.1", 11435))
        assert attempted == [("127.0.0.1", 11435)]
        connection.close()
    finally:
        socket.socket.connect = original
