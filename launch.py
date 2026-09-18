"""Launch from the project directory with its local tools on PATH."""
import os
from pathlib import Path
import runpy
import sys


def prepare_environment():
    project = Path(__file__).resolve().parent
    os.chdir(project)
    tool_dirs = [Path(sys.executable).parent]
    tool_dirs.extend(sorted((project / ".tools" / "ffmpeg").glob("*/bin")))
    tool_dirs.append(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "7-Zip")
    os.environ["PATH"] = os.pathsep.join(map(str, tool_dirs)) + os.pathsep + os.environ.get("PATH", "")
    return project


if __name__ == "__main__":
    project = prepare_environment()
    runpy.run_path(str(project / "gui.py"), run_name="__main__")
