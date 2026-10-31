import subprocess
import re
import shutil


def find_java() -> str | None:
    """Return path to java executable, or None if not found."""
    return shutil.which("java")


def get_java_version(java_path: str) -> int | None:
    """Parse 'java -version' output to get the major version number."""
    result = subprocess.run(
        [java_path, "-version"],
        capture_output=True, text=True
    )
    # java -version prints to stderr, not stdout
    output = result.stderr
    match = re.search(r'version "(\d+)', output)
    if match:
        return int(match.group(1))
    return None
