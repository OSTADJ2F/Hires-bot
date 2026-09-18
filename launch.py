"""Launch from the project directory with its local tools on PATH."""
import os
from pathlib import Path
import runpy
import sys


def _seven_zip_dir(project):
    """Directory of the user-configured 7-Zip executable (config.txt)."""
    try:
        lines = (project / "config.txt").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip().lower().replace("_", "").replace(" ", "") != "sevenzippath":
            continue
        v = v.strip().strip('"')
        if not v:
            return None
        p = Path(v)
        return p.parent if p.suffix else p
    return None


def prepare_environment():
    project = Path(__file__).resolve().parent
    os.chdir(project)
    tool_dirs = [Path(sys.executable).parent]
    tool_dirs.extend(sorted((project / ".tools" / "ffmpeg").glob("*/bin")))
    seven_zip_dir = _seven_zip_dir(project)
    if seven_zip_dir is not None:
        tool_dirs.append(seven_zip_dir)
    os.environ["PATH"] = os.pathsep.join(map(str, tool_dirs)) + os.pathsep + os.environ.get("PATH", "")
    return project


if __name__ == "__main__":
    project = prepare_environment()
    runpy.run_path(str(project / "gui.py"), run_name="__main__")
