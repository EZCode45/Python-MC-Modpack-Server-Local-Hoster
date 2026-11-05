import subprocess
import threading
import asyncio
from collections import deque

from java import find_java


class ServerProcess:
    def __init__(self, instance_dir: str, jar_name: str, ram_mb: int):
        self.instance_dir = instance_dir
        self.jar_name = jar_name
        self.ram_mb = ram_mb
        self.process: subprocess.Popen | None = None

        self.console_buffer: deque[str] = deque(maxlen=500)
        self._reader_thread: threading.Thread | None = None
        self._subscribers: list[asyncio.Queue] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self):
        java_path = find_java()
        if java_path is None:
            raise RuntimeError(
                "Java was not found on PATH. Install a JDK (Java 21 recommended) "
                "and make sure 'java' is available in the environment running this program."
            )
        cmd = [
            java_path, f"-Xmx{self.ram_mb}M", f"-Xms{self.ram_mb}M",
            "-jar", self.jar_name, "nogui"
        ]
        self.process = subprocess.Popen(
            cmd,
            cwd=self.instance_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._loop = asyncio.get_event_loop()
        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()

    def _read_output(self):
        if not self.process or not self.process.stdout:
            return
        for line in self.process.stdout:
            line = line.rstrip("\n")
            self.console_buffer.append(line)
            self._broadcast(line)
        self._broadcast("[process exited]")

    def _broadcast(self, line: str):
        if self._loop is None:
            return
        for q in list(self._subscribers):
            self._loop.call_soon_threadsafe(q.put_nowait, line)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    def send_command(self, command: str):
        if self.process and self.process.stdin:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

    def stop(self, timeout: int = 30):
        if not self.is_running():
            return
        self.send_command("stop")
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()

    def restart(self):
        self.stop()
        self.start()

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None