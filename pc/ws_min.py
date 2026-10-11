"""Small, standard-library RFC 6455 client for the Steam CDP connection.

The public API matches the subset of websocket-client used by the PC service:
create_connection(), send(), recv(), settimeout(), and close(). Strings are sent
as text; bytes are sent as binary. recv() returns str/bytes, or an empty string
on a peer close. Later operations raise WebSocketConnectionClosedException.

No proxy, extensions, compression, redirects, authentication, or subprotocols
are negotiated. Client frames are always masked; sends and receives have their
own locks. A receive timeout keeps both partial wire data and message fragments
so the next recv() can finish the same message. A send timeout closes the socket
because a partially transmitted frame cannot safely be retried.
"""

import base64
import hashlib
import hmac
import os
import socket
import ssl
import struct
import threading
import time
from urllib.parse import urlsplit


MAX_MESSAGE_BYTES = 64 * 1024 * 1024
MAX_HANDSHAKE_BYTES = 16 * 1024
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_OP_CONT, _OP_TEXT, _OP_BINARY = 0, 1, 2
_OP_CLOSE, _OP_PING, _OP_PONG = 8, 9, 10
_VALID_OPCODES = {_OP_CONT, _OP_TEXT, _OP_BINARY, _OP_CLOSE, _OP_PING, _OP_PONG}


class WebSocketException(Exception):
    """Base transport/handshake error, compatible with the service's catch-all."""


class WebSocketTimeoutException(WebSocketException, TimeoutError):
    """Socket timeout; incomplete received messages remain available."""


class WebSocketConnectionClosedException(WebSocketException):
    """The TCP/WebSocket connection is no longer usable."""


class WebSocketProtocolException(WebSocketException):
    """Invalid frame, close payload, UTF-8, or oversized message."""


def _close_code_valid(code):
    return (1000 <= code <= 1014 and code not in {1004, 1005, 1006}) or 3000 <= code <= 4999


def _parse_url(url):
    if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise ValueError("WebSocket URL contains whitespace or control characters")
    parts = urlsplit(url)
    if parts.scheme not in {"ws", "wss"} or not parts.hostname:
        raise ValueError("Expected a ws:// or wss:// URL with a host")
    if parts.username is not None or parts.password is not None or parts.fragment:
        raise ValueError("Authentication and fragments are not supported in WebSocket URLs")
    port = parts.port if parts.port is not None else (443 if parts.scheme == "wss" else 80)
    if not 1 <= port <= 65535:
        raise ValueError("Invalid WebSocket port")
    hostname = parts.hostname.encode("idna").decode("ascii")
    host = f"[{hostname}]" if ":" in hostname else hostname
    if parts.port is not None:
        host += f":{port}"
    target = parts.path or "/"
    if parts.query:
        target += "?" + parts.query
    try:
        target.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("WebSocket URL path must use percent-encoded non-ASCII characters") from exc
    return parts.scheme, hostname, port, host, target


def _handshake(sock, host, target, scheme, timeout, suppress_origin):
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    lines = [
        f"GET {target} HTTP/1.1", f"Host: {host}", "Upgrade: websocket",
        "Connection: Upgrade", f"Sec-WebSocket-Key: {key}", "Sec-WebSocket-Version: 13",
    ]
    if not suppress_origin:
        lines.append(f"Origin: {'https' if scheme == 'wss' else 'http'}://{host}")
    deadline = None if timeout is None else time.monotonic() + timeout
    response = bytearray()
    try:
        sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("ascii"))
        while True:
            end = response.find(b"\r\n\r\n")
            if end >= 0:
                if end + 4 > MAX_HANDSHAKE_BYTES:
                    raise WebSocketException("WebSocket handshake headers are too large")
                break
            if len(response) >= MAX_HANDSHAKE_BYTES:
                raise WebSocketException("WebSocket handshake headers are too large")
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WebSocketTimeoutException("WebSocket handshake timed out")
                sock.settimeout(remaining)
            chunk = sock.recv(min(4096, MAX_HANDSHAKE_BYTES - len(response)))
            if not chunk:
                raise WebSocketConnectionClosedException("Peer disconnected during WebSocket handshake")
            response.extend(chunk)
    except socket.timeout as exc:
        raise WebSocketTimeoutException("WebSocket handshake timed out") from exc
    finally:
        sock.settimeout(timeout)
    header_lines = bytes(response[:end]).decode("iso-8859-1").split("\r\n")
    status = header_lines[0].split(" ", 2)
    if len(status) < 2 or status[:2] != ["HTTP/1.1", "101"]:
        raise WebSocketException("Peer did not accept the WebSocket upgrade")
    headers = {}
    for line in header_lines[1:]:
        name, separator, value = line.partition(":")
        if not separator or not name or any(char not in "!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" for char in name):
            raise WebSocketException("Malformed WebSocket handshake header")
        if any(ord(char) < 32 and char != "\t" or ord(char) == 127 for char in value):
            raise WebSocketException("Malformed WebSocket handshake header value")
        headers.setdefault(name.lower(), []).append(value.strip())
    if [value.lower() for value in headers.get("upgrade", [])] != ["websocket"]:
        raise WebSocketException("Missing WebSocket Upgrade header")
    connection_tokens = ",".join(headers.get("connection", [])).lower().split(",")
    if "upgrade" not in [token.strip() for token in connection_tokens]:
        raise WebSocketException("Missing Connection: Upgrade header")
    expected = base64.b64encode(hashlib.sha1((key + _GUID).encode("ascii")).digest()).decode("ascii")
    accepts = headers.get("sec-websocket-accept", [])
    if len(accepts) != 1 or not hmac.compare_digest(accepts[0].encode("iso-8859-1"), expected.encode("ascii")):
        raise WebSocketException("Invalid Sec-WebSocket-Accept header")
    if "sec-websocket-extensions" in headers or "sec-websocket-protocol" in headers:
        raise WebSocketException("Peer selected an unrequested WebSocket extension or subprotocol")
    return response[end + 4:]


class WebSocket:
    """A connected transport. One reader and concurrent writers are supported."""

    def __init__(self, sock, buffered=b""):
        self.sock = sock
        self.connected = True
        self._send_lock = threading.RLock()
        self._recv_lock = threading.Lock()
        self._buffer = bytearray(buffered)
        self._fragment_opcode = None
        self._fragments = bytearray()
        self._max_message = MAX_MESSAGE_BYTES

    def settimeout(self, timeout):
        """Set the socket timeout in seconds; None waits indefinitely."""
        self.sock.settimeout(timeout)

    def _shutdown(self, drain=False):
        self.connected = False
        if drain:
            # Closing a TCP socket with unread bytes can send RST and discard
            # the protocol-close frame (notably on Windows). The receive owner
            # drains a bounded amount/time after shutting down its write side.
            deadline = time.monotonic() + 0.2
            remaining_bytes = 65536
            try:
                self.sock.shutdown(socket.SHUT_WR)
                while remaining_bytes:
                    remaining_time = deadline - time.monotonic()
                    if remaining_time <= 0:
                        break
                    self.sock.settimeout(remaining_time)
                    data = self.sock.recv(min(4096, remaining_bytes))
                    if not data:
                        break
                    remaining_bytes -= len(data)
            except OSError:
                pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()

    def _send_frame(self, payload, opcode):
        with self._send_lock:
            if not self.connected:
                raise WebSocketConnectionClosedException("WebSocket is closed")
            size = len(payload)
            if size < 126:
                header = bytes((0x80 | opcode, 0x80 | size))
            elif size <= 0xFFFF:
                header = bytes((0x80 | opcode, 0xFE)) + struct.pack("!H", size)
            else:
                header = bytes((0x80 | opcode, 0xFF)) + struct.pack("!Q", size)
            mask = os.urandom(4)
            masked = bytearray(payload)
            for index, key in enumerate(mask):
                masked[index::4] = masked[index::4].translate(bytes(value ^ key for value in range(256)))
            try:
                self.sock.sendall(header + mask)
                self.sock.sendall(masked)
            except socket.timeout as exc:
                self._shutdown()
                raise WebSocketTimeoutException("WebSocket send timed out; connection closed") from exc
            except OSError as exc:
                self._shutdown()
                raise WebSocketConnectionClosedException("WebSocket send failed") from exc

    def send(self, payload):
        """Send a complete text (str) or binary (bytes-like) message."""
        if isinstance(payload, str):
            data, opcode = payload.encode("utf-8"), _OP_TEXT
        elif isinstance(payload, (bytes, bytearray, memoryview)):
            data, opcode = bytes(payload), _OP_BINARY
        else:
            raise TypeError("WebSocket payload must be str or bytes-like")
        if len(data) > self._max_message:
            raise ValueError("WebSocket message exceeds the 64 MiB limit")
        self._send_frame(data, opcode)
        return len(data)

    def _ensure(self, size):
        # Nothing is consumed until the entire frame is present. A timeout can
        # therefore safely resume halfway through either its header or payload.
        while len(self._buffer) < size:
            if not self.connected:
                raise WebSocketConnectionClosedException("WebSocket is closed")
            try:
                data = self.sock.recv(min(65536, size - len(self._buffer)))
            except socket.timeout as exc:
                raise WebSocketTimeoutException("WebSocket receive timed out") from exc
            except OSError as exc:
                self._shutdown()
                raise WebSocketConnectionClosedException("WebSocket receive failed") from exc
            if not data:
                self._shutdown()
                raise WebSocketConnectionClosedException("Peer disconnected without a WebSocket close")
            self._buffer.extend(data)

    def _protocol_error(self, message, code=1002):
        try:
            self._send_frame(struct.pack("!H", code), _OP_CLOSE)
        except WebSocketException:
            pass
        finally:
            self._shutdown(drain=True)
        raise WebSocketProtocolException(message)

    def _read_frame(self):
        self._ensure(2)
        first, second = self._buffer[:2]
        fin, opcode = bool(first & 0x80), first & 0x0F
        if first & 0x70 or opcode not in _VALID_OPCODES or second & 0x80:
            self._protocol_error("Reserved bits/opcode or masked server frame")
        size, header_size = second & 0x7F, 2
        if opcode >= 8 and (not fin or size > 125):
            self._protocol_error("Control frames must be final and at most 125 bytes")
        if size == 126:
            self._ensure(4)
            size, header_size = struct.unpack("!H", self._buffer[2:4])[0], 4
            if size < 126:
                self._protocol_error("Non-minimal frame length encoding")
        elif size == 127:
            self._ensure(10)
            size, header_size = struct.unpack("!Q", self._buffer[2:10])[0], 10
            if size < 65536 or size & (1 << 63):
                self._protocol_error("Invalid 64-bit frame length")
        if size > self._max_message:
            self._protocol_error("WebSocket frame exceeds message limit", 1009)
        if opcode == _OP_CONT and self._fragment_opcode is None:
            self._protocol_error("Continuation frame without an initial fragment")
        if opcode in {_OP_TEXT, _OP_BINARY} and self._fragment_opcode is not None:
            self._protocol_error("New message before previous fragments finished")
        if opcode in {_OP_CONT, _OP_TEXT, _OP_BINARY} and len(self._fragments) + size > self._max_message:
            self._protocol_error("Fragmented WebSocket message exceeds message limit", 1009)
        self._ensure(header_size + size)
        payload = bytes(self._buffer[header_size:header_size + size])
        del self._buffer[:header_size + size]
        return fin, opcode, payload

    def recv(self):
        """Read a full message, automatically responding to ping and close."""
        with self._recv_lock:
            if not self.connected:
                raise WebSocketConnectionClosedException("WebSocket is closed")
            while True:
                fin, opcode, payload = self._read_frame()
                if opcode == _OP_PING:
                    self._send_frame(payload, _OP_PONG)
                    continue
                if opcode == _OP_PONG:
                    continue
                if opcode == _OP_CLOSE:
                    if len(payload) == 1:
                        self._protocol_error("Close frame contains an incomplete status code")
                    if payload:
                        if not _close_code_valid(struct.unpack("!H", payload[:2])[0]):
                            self._protocol_error("Close frame contains an invalid status code")
                        try:
                            payload[2:].decode("utf-8")
                        except UnicodeDecodeError:
                            self._protocol_error("Close reason is not valid UTF-8", 1007)
                    try:
                        self._send_frame(payload, _OP_CLOSE)
                    finally:
                        self._shutdown()
                    return ""
                if opcode != _OP_CONT:
                    self._fragment_opcode = opcode
                self._fragments.extend(payload)
                if not fin:
                    continue
                message = bytes(self._fragments)
                message_opcode = self._fragment_opcode
                self._fragments.clear()
                self._fragment_opcode = None
                if message_opcode == _OP_BINARY:
                    return message
                try:
                    return message.decode("utf-8")
                except UnicodeDecodeError:
                    self._protocol_error("Text message is not valid UTF-8", 1007)

    def close(self, status=1000, reason=b"", timeout=1):
        """Send close, then release the socket without awaiting a peer reply.

        A bounded send-lock wait also allows close() to unblock another thread
        stuck in send()/recv(). The CDP worker handles reconnecting separately.
        """
        if not self.connected:
            return
        if isinstance(reason, str):
            reason = reason.encode("utf-8")
        else:
            reason = bytes(reason)
        reason.decode("utf-8")
        if not _close_code_valid(status) or len(reason) > 123:
            raise ValueError("Invalid WebSocket close code or reason")
        if timeout is None or timeout <= 0:
            timeout = 1
        acquired = self._send_lock.acquire(timeout=timeout)
        try:
            if acquired and self.connected:
                previous = self.sock.gettimeout()
                self.sock.settimeout(timeout if previous is None else min(previous, timeout))
                try:
                    self._send_frame(struct.pack("!H", status) + reason, _OP_CLOSE)
                except WebSocketException:
                    pass
        finally:
            self._shutdown()
            if acquired:
                self._send_lock.release()


def create_connection(url, timeout=None, suppress_origin=False, enable_multithread=True):
    """Connect directly to ws/wss; locking is always enabled for safe sends."""
    scheme, hostname, port, host, target = _parse_url(url)
    sock = None
    try:
        sock = socket.create_connection((hostname, port), timeout=timeout)
        if scheme == "wss":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=hostname)
        buffered = _handshake(sock, host, target, scheme, timeout, suppress_origin)
        return WebSocket(sock, buffered)
    except socket.timeout as exc:
        if sock is not None:
            sock.close()
        raise WebSocketTimeoutException("WebSocket connection timed out") from exc
    except BaseException:
        if sock is not None:
            sock.close()
        raise
