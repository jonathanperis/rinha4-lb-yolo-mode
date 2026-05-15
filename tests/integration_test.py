#!/usr/bin/env python3
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

BIN = Path(sys.argv[1] if len(sys.argv) > 1 else "build/rinha4-lb-yolo-mode").resolve()


def wait_tcp(port: int, timeout: float = 3.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.05):
                return
        except OSError as exc:
            last = exc
            time.sleep(0.02)
    raise RuntimeError(f"port {port} did not open: {last}")


def http_get(port: int) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=2) as s:
        s.sendall(b"GET /ready HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        chunks = []
        expected = None
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
            joined = b"".join(chunks)
            header_end = joined.find(b"\r\n\r\n")
            if header_end >= 0 and expected is None:
                headers = joined[:header_end].decode("latin1").split("\r\n")
                for line in headers:
                    if line.lower().startswith("content-length:"):
                        expected = header_end + 4 + int(line.split(":", 1)[1].strip())
                        break
            if expected is not None and len(joined) >= expected:
                break
        return b"".join(chunks)


def http_get_after_accept_delay(port: int) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=2) as s:
        time.sleep(0.05)
        s.sendall(b"GET /ready HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
            if b"fdpass-" in b"".join(chunks):
                break
        return b"".join(chunks)


def unix_http_server(path: Path, body: bytes, stop: threading.Event) -> threading.Thread:
    def run() -> None:
        try:
            path.unlink(missing_ok=True)
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(str(path))
            srv.listen(32)
            srv.settimeout(0.1)
            response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\nConnection: keep-alive\r\n\r\n" + body
            while not stop.is_set():
                try:
                    conn, _ = srv.accept()
                except socket.timeout:
                    continue
                with conn:
                    conn.settimeout(0.5)
                    req = conn.recv(4096)
                    if not req:
                        continue
                    try:
                        conn.sendall(response)
                    except BrokenPipeError:
                        pass
                    try:
                        conn.recv(4096)
                    except socket.timeout:
                        pass
        finally:
            try:
                srv.close()
            except Exception:
                pass
            path.unlink(missing_ok=True)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def recv_fd(conn: socket.socket) -> int:
    msg, ancdata, *_ = conn.recvmsg(1, socket.CMSG_SPACE(struct.calcsize("i")))
    if not msg:
        raise RuntimeError("control socket closed")
    for level, ctype, data in ancdata:
        if level == socket.SOL_SOCKET and ctype == socket.SCM_RIGHTS:
            return struct.unpack("i", data[: struct.calcsize("i")])[0]
    raise RuntimeError("no fd received")


def fdpass_server(path: Path, body: bytes, stop: threading.Event) -> threading.Thread:
    def run() -> None:
        try:
            path.unlink(missing_ok=True)
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(str(path))
            srv.listen(32)
            srv.settimeout(0.1)
            response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body
            controls = []
            while not stop.is_set():
                try:
                    conn, _ = srv.accept()
                    conn.settimeout(0.1)
                    controls.append(conn)
                except socket.timeout:
                    pass
                alive = []
                for conn in controls:
                    try:
                        fd = recv_fd(conn)
                    except socket.timeout:
                        alive.append(conn)
                        continue
                    except OSError:
                        conn.close()
                        continue
                    with socket.socket(fileno=fd) as client:
                        _ = client.recv(4096)
                        client.sendall(response)
                    alive.append(conn)
                controls = alive
        finally:
            for conn in locals().get("controls", []):
                try:
                    conn.close()
                except Exception:
                    pass
            try:
                srv.close()
            except Exception:
                pass
            path.unlink(missing_ok=True)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def run_lb(env: dict[str, str]) -> subprocess.Popen:
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.Popen([str(BIN)], env=merged, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_proxy(tmp: Path) -> None:
    stop = threading.Event()
    s1 = tmp / "api1.sock"
    s2 = tmp / "api2.sock"
    unix_http_server(s1, b"proxy-1", stop)
    unix_http_server(s2, b"proxy-2", stop)
    deadline = time.time() + 2
    while time.time() < deadline and not (s1.exists() and s2.exists()):
        time.sleep(0.01)
    port = 18081
    proc = run_lb({"LB_MODE": "proxy", "PORT": str(port), "UPSTREAMS": f"{s1},{s2}"})
    try:
        wait_tcp(port)
        out = http_get(port)
        assert b"HTTP/1.1 200 OK" in out, out
        assert b"proxy-" in out, out
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        stop.set()


def test_fdpass(tmp: Path) -> None:
    stop = threading.Event()
    s1 = tmp / "fd1.sock"
    s2 = tmp / "fd2.sock"
    fdpass_server(s1, b"fdpass-1", stop)
    fdpass_server(s2, b"fdpass-2", stop)
    # Give control sockets a moment to bind; fdpass mode connects before listening.
    deadline = time.time() + 2
    while time.time() < deadline and not (s1.exists() and s2.exists()):
        time.sleep(0.01)
    port = 18082
    proc = run_lb({"LB_MODE": "fdpass", "PORT": str(port), "UPSTREAMS": f"{s1},{s2}"})
    try:
        wait_tcp(port)
        delayed = http_get_after_accept_delay(port)
        assert b"HTTP/1.1 200 OK" in delayed, delayed
        assert b"fdpass-" in delayed, delayed
        out = http_get(port)
        assert b"HTTP/1.1 200 OK" in out, out
        assert b"fdpass-" in out, out
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        stop.set()


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        test_proxy(tmp)
        test_fdpass(tmp)
    print("integration tests passed")


if __name__ == "__main__":
    main()
