import subprocess
import re
import shutil
import glob
import os
import platform


def _search_common_locations() -> str | None:
    """Fallback search when 'java' isn't resolvable via PATH.
    Checks typical JDK install directories directly."""
    system = platform.system()

    if system == "Windows":
        patterns = [
            r"C:\Program Files\Java\*\bin\java.exe",
            r"C:\Program Files\Eclipse Adoptium\*\bin\java.exe",
            r"C:\Program Files (x86)\Java\*\bin\java.exe",
        ]
    elif system == "Darwin":
        patterns = [
            "/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java",
            "/opt/homebrew/opt/openjdk*/bin/java",
            "/usr/local/opt/openjdk*/bin/java",
        ]
    else:  # Linux
        patterns = [
            "/usr/lib/jvm/*/bin/java",
            "/usr/java/*/bin/java",
        ]

    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    # prefer the newest-looking path (simple heuristic: sort descending)
    candidates.sort(reverse=True)
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def find_java() -> str | None:
    """Return path to java executable, or None if not found.
    First checks PATH, then falls back to common install locations
    (useful on Windows where PATH isn't always inherited by every process)."""
    path = shutil.which("java")
    if path:
        return path
    return _search_common_locations()


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