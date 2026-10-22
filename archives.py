"""Reading and extracting the .rar sources with The Unarchiver's command line tools (unar, lsar)."""
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

RAR_SIGNATURE = b"Rar!"
INSTALL_HINT = ("The sources are .rar archives, which need The Unarchiver's command line tools "
                "(unar and lsar):\n"
                "  macOS:  brew install unar\n"
                "  Linux:  sudo apt install unar\n"
                "  Windows: https://theunarchiver.com/command-line")


class ArchiveError(Exception):
    """Raised when an archive cannot be listed or extracted; the message is user-facing."""


@dataclass(frozen=True)
class ArchiveEntry:
    index: int
    name: str    # path inside the archive, '/' separated
    size: int
    is_dir: bool


def looks_like_rar(path):
    """Cheap check that a file is a RAR archive (the signature starts the file)."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == RAR_SIGNATURE
    except OSError:
        return False


class ArchiveTool:
    def __init__(self):
        self.unar = shutil.which("unar")
        self.lsar = shutil.which("lsar")

    @property
    def available(self):
        return bool(self.unar and self.lsar)

    def require(self):
        if not self.available:
            raise ArchiveError(INSTALL_HINT)

    def entries(self, archive):
        """Every file and folder in `archive`."""
        self.require()
        done = subprocess.run([self.lsar, "-j", str(archive)], capture_output=True)
        if done.returncode != 0:
            raise ArchiveError(f"Cannot read {Path(archive).name}: "
                               f"{done.stderr.decode(errors='replace').strip()}")
        listing = json.loads(done.stdout)["lsarContents"]
        return [ArchiveEntry(e["XADIndex"], e["XADFileName"].replace("\\", "/"),
                             int(e.get("XADFileSize", 0)), bool(e.get("XADIsDirectory")))
                for e in listing]

    def extract(self, archive, indexes, dest):
        """Extract the entries with these `indexes` into `dest`, keeping their paths."""
        self.require()
        cmd = [self.unar, "-quiet", "-no-directory", "-no-recursion", "-force-overwrite",
               "-output-directory", str(dest), "-indexes", str(archive), *map(str, indexes)]
        done = subprocess.run(cmd, capture_output=True)
        if done.returncode != 0:
            raise ArchiveError(f"Cannot extract from {Path(archive).name}: "
                               f"{done.stderr.decode(errors='replace').strip() or done.stdout.decode(errors='replace').strip()}")
