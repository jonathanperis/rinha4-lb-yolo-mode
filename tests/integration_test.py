#!/usr/bin/env python3
import fcntl
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


def http_get_split_headers(port: int) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=2) as s:
        s.sendall(b"GET /ready HTTP/1.1\r\nHost: local")
        time.sleep(0.01)
        s.sendall(b"host\r\nConnection: close\r\n\r\n")
        chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data)
            if b"proxy-" in b"".join(chunks):
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
                    req = b""
                    while b"\r\n\r\n" not in req:
                        try:
                            chunk = conn.recv(4096)
                        except socket.timeout:
                            break
                        if not chunk:
                            break
                        req += chunk
                    if not req or b"\r\n\r\n" not in req:
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


def fdpass_server(path: Path, body: bytes, stop: threading.Event, sock_type: int = socket.SOCK_SEQPACKET) -> threading.Thread:
    def run() -> None:
        try:
            path.unlink(missing_ok=True)
            srv = socket.socket(socket.AF_UNIX, sock_type)
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
                    except (OSError, RuntimeError):
                        conn.close()
                        continue
                    with socket.socket(fileno=fd) as client:
                        status_flags = fcntl.fcntl(client.fileno(), fcntl.F_GETFL)
                        assert not (status_flags & os.O_NONBLOCK), "fdpass client fd must be blocking for assembly-style backends"
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
        split = http_get_split_headers(port)
        assert b"HTTP/1.1 200 OK" in split, split
        assert b"proxy-" in split, split
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        stop.set()


def test_fdpass(tmp: Path, sock_type: int = socket.SOCK_SEQPACKET, extra_env: dict[str, str] | None = None) -> None:
    stop = threading.Event()
    s1 = tmp / f"fd1-{sock_type}.sock"
    s2 = tmp / f"fd2-{sock_type}.sock"
    fdpass_server(s1, b"fdpass-1", stop, sock_type)
    fdpass_server(s2, b"fdpass-2", stop, sock_type)
    # Give control sockets a moment to bind; fdpass mode connects before listening.
    deadline = time.time() + 2
    while time.time() < deadline and not (s1.exists() and s2.exists()):
        time.sleep(0.01)
    port = 18082
    env = {"LB_MODE": "fdpass", "PORT": str(port), "UPSTREAMS": f"{s1},{s2}"}
    if extra_env:
        env.update(extra_env)
    proc = run_lb(env)
    try:
        wait_tcp(port)
        delayed = http_get_after_accept_delay(port)
        assert b"HTTP/1.1 200 OK" in delayed, delayed
        assert b"fdpass-" in delayed, delayed
        bodies = [delayed]
        for _ in range(4):
            out = http_get(port)
            assert b"HTTP/1.1 200 OK" in out, out
            assert b"fdpass-" in out, out
            bodies.append(out)
        joined = b"\n".join(bodies)
        assert b"fdpass-1" in joined and b"fdpass-2" in joined, joined
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        stop.set()


def assert_exits_nonzero(env: dict[str, str], *, code: int | None = None, needle: bytes = b"") -> None:
    proc = run_lb(env)
    try:
        rc = proc.wait(timeout=2)
        stderr = proc.stderr.read() if proc.stderr else b""
        assert rc != 0, f"expected failure for {env}"
        if code is not None:
            assert rc == code, (env, rc, stderr)
        if needle:
            assert needle.lower() in stderr.lower(), (env, rc, stderr)
    finally:
        if proc.poll() is None:
            proc.kill()


def test_invalid_lb_modes(tmp: Path) -> None:
    upstreams = f"{tmp / 'missing1.sock'},{tmp / 'missing2.sock'}"
    for value in ("foo", "fdpass-garbage"):
        assert_exits_nonzero(
            {"LB_MODE": value, "PORT": "18183", "UPSTREAMS": upstreams},
            code=2,
            needle=b"unsupported",
        )


def test_bad_upstreams_rejected(tmp: Path) -> None:
    long_path = "/" + ("x" * 108)
    cases = [
        "",
        str(tmp / "only-one.sock"),
        f",{tmp / 'api2.sock'}",
        f"{tmp / 'api1.sock'},",
        f"{tmp / 'api1.sock'},{tmp / 'api2.sock'},{tmp / 'api3.sock'}",
        f"{long_path},{tmp / 'api2.sock'}",
        f"{tmp / 'api1.sock'},{long_path}",
    ]
    for idx, upstreams in enumerate(cases):
        assert_exits_nonzero(
            {"LB_MODE": "fdpass", "PORT": str(18200 + idx), "UPSTREAMS": upstreams},
            needle=b"invalid",
        )


def test_invalid_port_uses_default(tmp: Path) -> None:
    stop = threading.Event()
    s1 = tmp / "default-port-fd1.sock"
    s2 = tmp / "default-port-fd2.sock"
    fdpass_server(s1, b"fdpass-1", stop)
    fdpass_server(s2, b"fdpass-2", stop)
    deadline = time.time() + 2
    while time.time() < deadline and not (s1.exists() and s2.exists()):
        time.sleep(0.01)
    proc = run_lb({"LB_MODE": "fdpass", "PORT": "70000", "BACKLOG": "0", "UPSTREAMS": f"{s1},{s2}"})
    try:
        wait_tcp(9999)
        out = http_get(9999)
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
    modes = {m.strip() for m in os.environ.get("LB_TEST_MODES", "proxy,fdpass").split(",") if m.strip()}
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        if "proxy" in modes:
            test_proxy(tmp)
        if "fdpass" in modes:
            test_fdpass(tmp)
            test_fdpass(tmp, socket.SOCK_STREAM, {"LB_FDPASS_SOCKET_TYPE": "stream"})
        if "invalid-lb-mode" in modes:
            test_invalid_lb_modes(tmp)
        if "bad-upstreams" in modes:
            test_bad_upstreams_rejected(tmp)
        if "parse-dec" in modes:
            test_invalid_port_uses_default(tmp)
    print("integration tests passed")


if __name__ == "__main__":
    main()
