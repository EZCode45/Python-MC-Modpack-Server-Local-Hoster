import subprocess
import re
import shutil

def find_java() -> str | None:
    """Return Path to java exec or none if not found."""
    return shutil.which("java")


def get_java_version(java_path: str) -> str | None:
    """Parse 'Java -version' output and return the version number."""
    result = subprocess.run(
        [java_path, "-version"],
        capture_output=True, text=True
    )
    # Java -version prints to stderr not stdout
    output = result.stderr
    match = re.search(r'version "(\d+)', output)
    if match:
        return int(match.group(1))
    return None