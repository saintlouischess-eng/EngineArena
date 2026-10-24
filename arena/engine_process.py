"""UCI pipe receipt timestamps independent of the application's asyncio loop.

Only pipe I/O and a small bestmove receipt run on reader threads. Protocol
parsing, UI callbacks and all game/database state remain on the owning loop.
Engine-reported search time is never used to decide a chess-clock result.
"""
from __future__ import annotations

import asyncio
from collections import deque
import subprocess
import threading
import time


class SearchReceipt:
    def __init__(self):
        self._lock = threading.Lock()
        self._result = None

    def observe(self, line, stamp):
        if not line.lstrip().startswith(b'bestmove '):
            return
        words = line.split()
        if len(words) >= 2 and words[0] == b'bestmove':
            result = (words[1].decode('utf-8', 'replace'), stamp,
                      words[3].decode('utf-8', 'replace') if len(words) >= 4 and words[2] == b'ponder' else None)
            with self._lock:
                if self._result is None:
                    self._result = result

    def snapshot(self):
        with self._lock:
            return self._result


class ReceivedLine(bytes):
    def __new__(cls, raw, received, receipt=None):
        value = super().__new__(cls, raw)
        value.received = received
        value.receipt = receipt
        return value


class PipeReader:
    MAX_LINE = 65536
    MAX_BYTES = 2 * 1024 * 1024
    MAX_LINES = 4096

    def __init__(self, pipe, loop, *, stdout):
        self.pipe = pipe
        self.loop = loop
        self.stdout = stdout
        self._lock = threading.Lock()
        self._lines = deque()
        self._bytes = 0
        self._ended = False
        self._error = None
        self._receipt = None
        self._notified = False
        self._event = asyncio.Event()
        self.discarded_info = 0
        self.thread = threading.Thread(target=self._read, name='UciStdout' if stdout else 'UciStderr', daemon=True)
        self.thread.start()

    def arm(self):
        receipt = SearchReceipt()
        with self._lock:
            self._receipt = receipt
        return receipt

    def _notify(self):
        if not self._notified:
            self._notified = True
            try:
                self.loop.call_soon_threadsafe(self._event.set)
            except RuntimeError:
                pass  # The owning worker is already shutting down.

    def _read(self):
        try:
            while raw := self.pipe.readline(self.MAX_LINE + 1):
                stamp = time.perf_counter()
                if len(raw) > self.MAX_LINE:
                    raise ValueError('Engine output line exceeds 65536 bytes')
                with self._lock:
                    receipt = self._receipt
                    if self.stdout and receipt is not None:
                        receipt.observe(raw, stamp)
                    line = ReceivedLine(raw, stamp, receipt)
                    if self._bytes + len(raw) > self.MAX_BYTES or len(self._lines) >= self.MAX_LINES:
                        # Keep protocol replies while coalescing stale telemetry.
                        # Never stop draining stdout behind an info-output flood.
                        retained = deque(x for x in self._lines if self.stdout and not x.lstrip().startswith(b'info '))
                        self.discarded_info += len(self._lines) - len(retained)
                        self._lines = retained
                        self._bytes = sum(map(len, retained))
                    if self._bytes + len(raw) > self.MAX_BYTES or len(self._lines) >= self.MAX_LINES:
                        raise ValueError('Engine protocol output exceeds the bounded input queue')
                    self._lines.append(line)
                    self._bytes += len(line)
                    self._notify()
        except (OSError, ValueError) as error:
            with self._lock:
                self._error = error
        finally:
            with self._lock:
                self._ended = True
                self._notify()

    async def readline(self):
        while True:
            with self._lock:
                if self._lines:
                    line = self._lines.popleft()
                    self._bytes -= len(line)
                    return line
                if self._ended:
                    if self._error is not None:
                        raise self._error
                    return b''
                self._notified = False
                self._event.clear()
            await self._event.wait()


class PipeWriter:
    def __init__(self, pipe):
        self.pipe = pipe
        self.pending = bytearray()
        self._lock = threading.Lock()
        self.search_started = None

    def write(self, data):
        self.pending.extend(data)

    def _send(self, data):
        with self._lock:
            started = time.perf_counter()
            if data.startswith(b'go ') or data.startswith(b'ponderhit\n'):
                self.search_started = started
            self.pipe.write(data)
            self.pipe.flush()
            return started

    async def drain(self):
        data = bytes(self.pending)
        self.pending.clear()
        return await asyncio.to_thread(self._send, data)


class EngineProcess:
    def __init__(self, process, loop):
        self._process = process
        self.pid = process.pid
        self.stdin = PipeWriter(process.stdin)
        self.stdout = PipeReader(process.stdout, loop, stdout=True)
        self.stderr = PipeReader(process.stderr, loop, stdout=False)

    @classmethod
    async def create(cls, *args, **kwargs):
        loop = asyncio.get_running_loop()
        task = asyncio.create_task(asyncio.to_thread(subprocess.Popen, args,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs))
        try:
            process = await asyncio.shield(task)
        except asyncio.CancelledError:
            # A canceled launch must not leave an unowned engine behind.
            process = await task
            process.kill()
            await asyncio.to_thread(process.wait)
            for pipe in (process.stdin, process.stdout, process.stderr):
                pipe.close()
            raise
        return cls(process, loop)

    @property
    def returncode(self):
        return self._process.poll()

    async def wait(self):
        return await asyncio.to_thread(self._process.wait)

    def kill(self):
        self._process.kill()

    async def close_pipes(self):
        def close():
            for reader in (self.stdout, self.stderr):
                reader.thread.join(timeout=3)
                if not reader.thread.is_alive():
                    reader.pipe.close()
            try:
                self._process.stdin.close()
            except OSError:
                pass  # A crashed peer may have left a failed buffered write.
        await asyncio.to_thread(close)
