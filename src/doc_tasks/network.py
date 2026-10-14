"""Defense in depth: analysis processes may open only loopback TCP connections."""
import ipaddress
import socket


def install_local_network_guard():
    original = socket.socket.connect
    if getattr(original, "_doc_tasks_local_guard", False):
        return
    def guarded(connection, address):
        if connection.family in (socket.AF_INET, socket.AF_INET6):
            host = address[0]
            try:
                local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = host == "localhost"
            if not local:
                raise OSError("Local-only analysis forbids external network connections")
        return original(connection, address)
    guarded._doc_tasks_local_guard = True
    socket.socket.connect = guarded
