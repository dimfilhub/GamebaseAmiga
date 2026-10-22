"""Extract the .rar archives in sources/ into the data/ tree.

Usage: python3 populate.py [--dry-run]

Needs The Unarchiver's command line tools (unar, lsar); see README.md.
"""
import re
import shutil
import string
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

from archives import INSTALL_HINT, ArchiveError, ArchiveTool, looks_like_rar
from data_layout import DataLayout

CHUNK_FILES = 400            # extracted per unar call, so the staging folder stays small
CHUNK_BYTES = 1 << 30
GAME_FOLDER = re.compile(r"^[^/]/")  # the games are in one-letter folders: 0, A ... Z


@dataclass(frozen=True)
class Rule:
    """Entries of an archive whose path starts with `prefix` go to `dest` (prefix removed)."""
    prefix: str
    dest: Path
    only: Optional[re.Pattern] = None  # if set, the part after the prefix must match


class Populator:
    """Existing files with the same size are skipped, so it can be re-run safely."""

    def __init__(self, layout: DataLayout, log=print, tool=None):
        self.layout = layout
        self.log = log  # callable(str) receiving progress lines
        self.tool = tool or ArchiveTool()

    @property
    def plan(self):
        """archive (path relative to the sources folder) -> rules, first match wins.
        Entries no rule matches are ignored. Names are matched case-insensitively."""
        l = self.layout
        plan = {f"Games/{c}.rar": [Rule("", l.games, GAME_FOLDER)]
                for c in "0" + string.ascii_uppercase}
        plan["Screenshots.rar"] = [Rule("Screenshots/", l.screenshots)]
        plan["Music.rar"] = [Rule("Music/", l.music_dir)]
        plan["Extras.rar"] = [Rule("Extras/SPS/", l.extras_runnable / "SPS"),
                              Rule("Extras/WHDLoad/", l.extras_runnable / "WHDLoad"),
                              Rule("Extras/", l.extras_dir)]
        plan["WHD.rar"] = [Rule("WHD/", l.whd_dir)]
        return plan

    def _present(self, folder):
        """casefolded relative name -> real relative name of the .rar files in the sources folder
        (its top level and one level of sub-folders)."""
        if not folder.is_dir():
            return {}
        found = [*folder.glob("*.rar"), *folder.glob("*/*.rar")]
        return {p.relative_to(folder).as_posix().casefold(): p.relative_to(folder).as_posix()
                for p in found if p.is_file()}

    def check_sources(self, folder=None):
        """Compare `folder` (default: the sources folder) with the archives the plan expects.
        Returns (found, missing, broken, extra) lists of archive names."""
        folder = Path(folder or self.layout.sources)
        present = self._present(folder)
        expected = list(self.plan)
        found = [present[n.casefold()] for n in expected if n.casefold() in present]
        broken = [n for n in found if not looks_like_rar(folder / n)]
        found = [n for n in found if n not in broken]
        missing = [n for n in expected if n.casefold() not in present]
        wanted = {n.casefold() for n in expected}
        extra = sorted(n for k, n in present.items() if k not in wanted)
        return found, missing, broken, extra

    @staticmethod
    def route(name, rules):
        """Destination of the archive entry `name`, or None if no rule wants it."""
        parts = PurePosixPath(name).parts
        if not parts or name.startswith("__MACOSX") or parts[-1] == ".DS_Store":
            return None
        for rule in rules:
            if name.casefold().startswith(rule.prefix.casefold()):
                rest = name[len(rule.prefix):]
                if rule.only and not rule.only.match(rest):
                    continue
                rel = PurePosixPath(rest)
                if not rel.parts:
                    return None
                target = (rule.dest / Path(*rel.parts)).resolve()
                root = rule.dest.resolve()
                return target if root in target.parents else None  # zip-slip guard
        return None

    def extract(self, archive, rules, dry=False):
        """Returns (extracted, skipped) counts for one archive."""
        wanted, skipped = [], 0
        parents = {}  # parent folder -> its real on-disk path (case/Unicode-insensitive match)
        for entry in self.tool.entries(archive):
            if entry.is_dir:
                continue
            target = self.route(entry.name, rules)
            if target is None:
                continue
            if target.parent not in parents:
                parents[target.parent] = self.layout.resolve(target.parent)
            target = parents[target.parent] / target.name
            if target.exists() and target.stat().st_size == entry.size:
                skipped += 1
            else:
                wanted.append((entry, target))
        if not dry:
            self._extract_chunks(archive, wanted)
        return len(wanted), skipped

    def _extract_chunks(self, archive, wanted):
        stage = self.layout.cache / "extract" / Path(archive).stem
        done = 0
        try:
            chunk, size = [], 0
            for i, item in enumerate(wanted):
                chunk.append(item)
                size += item[0].size
                if len(chunk) >= CHUNK_FILES or size >= CHUNK_BYTES or i == len(wanted) - 1:
                    self._move_chunk(archive, chunk, stage)
                    done += len(chunk)
                    chunk, size = [], 0
                    if len(wanted) > CHUNK_FILES:
                        self.log(f"  {Path(archive).name}: {done}/{len(wanted)}")
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def _move_chunk(self, archive, chunk, stage):
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True)
        self.tool.extract(archive, [entry.index for entry, _ in chunk], stage)
        for entry, target in chunk:
            staged = stage / Path(*PurePosixPath(entry.name).parts)
            if not staged.is_file():
                self.log(f"  not extracted: {entry.name}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staged), str(target))

    def run(self, dry=False):
        found, missing, broken, _extra = self.check_sources()
        plan = {k.casefold(): v for k, v in self.plan.items()}
        for name in missing:
            self.log(f"missing: {name}")
        for name in broken:
            self.log(f"unreadable: {name}")
        if found and not self.tool.available:
            raise ArchiveError(INSTALL_HINT)
        for name in found:
            try:
                n, s = self.extract(self.layout.sources / name, plan[name.casefold()], dry)
            except ArchiveError as e:
                self.log(f"{name}: {e}")
                continue
            self.log(f"{name}: {'would extract' if dry else 'extracted'} {n}, skipped {s}")


if __name__ == "__main__":
    try:
        Populator(DataLayout()).run(dry="--dry-run" in sys.argv)
    except ArchiveError as e:
        sys.exit(str(e))
