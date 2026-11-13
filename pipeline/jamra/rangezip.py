"""Read single files out of a remote ZIP archive using HTTP range requests.

NASA FIRMS publishes one large ZIP per sensor and year ("all countries",
70-400 MB each). We only need a few countries, so instead of downloading the
whole archive we read the ZIP table of contents (central directory) and then
fetch only the bytes of the country files we need.

Note: code written with the help of an SI coding assistant (Claude Code).
"""
from __future__ import annotations

import http.client
import struct
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass

USER_AGENT = "jamra-pipeline/1.0 (NASA Space Apps 2026 project)"


@dataclass
class ZipEntry:
    name: str
    method: int
    compressed_size: int
    size: int
    header_offset: int


class RemoteZip:
    """Minimal ZIP reader over HTTP Range requests (deflate and stored only)."""

    def __init__(self, url: str, timeout: float = 90.0, retries: int = 6):
        self.url = url
        self.timeout = timeout
        self.retries = retries
        self.size = self._content_length()
        self.entries = self._read_central_directory()

    # ------------------------------------------------------------ http
    def _open(self, headers: dict[str, str], method: str = "GET") -> tuple[int, dict, bytes]:
        req = urllib.request.Request(
            self.url, headers={"User-Agent": USER_AGENT, **headers}, method=method
        )
        delay = 2.0
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return r.status, dict(r.headers.items()), r.read()
            except urllib.error.HTTPError as e:
                # 4xx (except 429) will not get better by retrying.
                if 400 <= e.code < 500 and e.code != 429:
                    raise
                last = e
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.HTTPException) as e:
                last = e
            if attempt == self.retries - 1:
                raise RuntimeError(f"Failed after {self.retries} tries: {self.url}: {last}")
            time.sleep(delay)
            delay = min(delay * 2, 60)
        raise RuntimeError("unreachable")

    def _content_length(self) -> int:
        _, headers, _ = self._open({}, method="HEAD")
        length = {k.lower(): v for k, v in headers.items()}.get("content-length")
        if not length:
            raise RuntimeError(f"No Content-Length for {self.url}")
        return int(length)

    def read_range(self, start: int, end: int) -> bytes:
        """Return bytes [start, end) of the remote file."""
        if end <= start:
            return b""
        status, _, body = self._open({"Range": f"bytes={start}-{end - 1}"})
        if status != 206 and len(body) != end - start:
            raise RuntimeError(f"Server ignored Range request for {self.url}")
        if len(body) != end - start:
            raise RuntimeError(f"Short read {len(body)} != {end - start} for {self.url}")
        return body

    # ------------------------------------------------------------- zip
    def _read_central_directory(self) -> list[ZipEntry]:
        tail_len = min(self.size, 65536 + 22)
        tail = self.read_range(self.size - tail_len, self.size)
        eocd = tail.rfind(b"PK\x05\x06")
        if eocd < 0:
            raise RuntimeError("End of central directory not found")
        (_, _, _, _, n_entries, cd_size, cd_offset, _) = struct.unpack(
            "<IHHHHIIH", tail[eocd : eocd + 22]
        )
        if cd_offset == 0xFFFFFFFF or cd_size == 0xFFFFFFFF or n_entries == 0xFFFF:
            loc = tail.rfind(b"PK\x06\x07")
            if loc < 0:
                raise RuntimeError("ZIP64 locator not found")
            (_, _, z64_off, _) = struct.unpack("<IIQI", tail[loc : loc + 20])
            z64 = self.read_range(z64_off, z64_off + 56)
            (_, _, _, _, _, _, n_entries, _, cd_size, cd_offset) = struct.unpack(
                "<IQHHIIQQQQ", z64
            )
        cd = self.read_range(cd_offset, cd_offset + cd_size)
        entries: list[ZipEntry] = []
        p = 0
        while p + 46 <= len(cd) and cd[p : p + 4] == b"PK\x01\x02":
            (
                _, _, _, flags, method, _, _, _, csize, usize, n_len, e_len, c_len,
                _, _, _, h_off,
            ) = struct.unpack("<IHHHHHHIIIHHHHHII", cd[p : p + 46])
            name_bytes = cd[p + 46 : p + 46 + n_len]
            name = name_bytes.decode("utf-8" if flags & 0x800 else "cp437")
            extra = cd[p + 46 + n_len : p + 46 + n_len + e_len]
            csize, usize, h_off = _apply_zip64(extra, csize, usize, h_off)
            entries.append(ZipEntry(name, method, csize, usize, h_off))
            p += 46 + n_len + e_len + c_len
        return entries

    def read_entry(self, entry: ZipEntry) -> bytes:
        head = self.read_range(entry.header_offset, entry.header_offset + 30)
        if head[:4] != b"PK\x03\x04":
            raise RuntimeError(f"Bad local header for {entry.name}")
        n_len, e_len = struct.unpack("<HH", head[26:30])
        start = entry.header_offset + 30 + n_len + e_len
        raw = self.read_range(start, start + entry.compressed_size)
        if entry.method == 0:
            data = raw
        elif entry.method == 8:
            data = zlib.decompress(raw, -15)
        else:
            raise RuntimeError(f"Unsupported compression method {entry.method}")
        if len(data) != entry.size:
            raise RuntimeError(f"Size mismatch for {entry.name}")
        return data


def _apply_zip64(extra: bytes, csize: int, usize: int, h_off: int) -> tuple[int, int, int]:
    """Read 64-bit sizes from the ZIP64 extra field when the 32-bit ones overflow."""
    p = 0
    while p + 4 <= len(extra):
        tag, size = struct.unpack("<HH", extra[p : p + 4])
        if tag == 0x0001:
            body = extra[p + 4 : p + 4 + size]
            q = 0
            if usize == 0xFFFFFFFF:
                usize = struct.unpack("<Q", body[q : q + 8])[0]
                q += 8
            if csize == 0xFFFFFFFF:
                csize = struct.unpack("<Q", body[q : q + 8])[0]
                q += 8
            if h_off == 0xFFFFFFFF:
                h_off = struct.unpack("<Q", body[q : q + 8])[0]
            break
        p += 4 + size
    return csize, usize, h_off
