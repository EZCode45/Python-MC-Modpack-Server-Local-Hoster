import subprocess

class ServerProcess:
    def __init__(self, instance_dir: str, jar_name: str, ram_mb: int):
        self.instance_dir = instance_dir
        self.jar_name = jar_name
        self.ram_mb = ram_mb
        self.process: subprocess.Popen | None = None

    def start(self):
        cmd = [
            "java", f"-Xmx{self.ram_mb}M", f"'Xms{self.ram_mb}M'",
            "-jar", self.jar_name, "nogui"
        ]
        self.process = subprocess.Popen(
            cmd,
            cwd=self.instance_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def send_command(self, command: str):
        if self.process and self.process.stdin:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

    def stop(self, timeout: int = 90):
        if not self.is_running():
            return
        self.send_command("stop")
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None