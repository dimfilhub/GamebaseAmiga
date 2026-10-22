"""Plain data objects returned by the repository."""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from text import clean, year_text

DISK_SUFFIX = re.compile(r"_(Disk\w+)\.zip$", re.I)


@dataclass(frozen=True)
class Game:
    """One row of the game list."""
    id: int
    name: str
    year: Optional[int]
    publisher: Optional[str]
    genre: Optional[str]
    parent_genre: Optional[str]
    filename: Optional[str]
    screenshot_filename: Optional[str]
    music_filename: Optional[str]
    developer: Optional[str]
    playable: bool = True  # the database has a game zip or a runnable extra (SPS/WHDLoad) for it

    @property
    def title(self):
        """Name for the list: games sold on several disks have one row per disk."""
        m = DISK_SUFFIX.search(self.filename or "")
        return f"{self.name} ({m.group(1)})" if m else self.name

    @property
    def year_text(self):
        return year_text(self.year)

    @property
    def publisher_text(self):
        return clean(self.publisher)

    @property
    def genre_text(self):
        return clean(self.genre)

    @property
    def developer_text(self):
        return clean(self.developer)


@dataclass(frozen=True)
class GameDetails:
    """Full record shown in the Info / Notes tabs."""
    name: str
    year: Optional[int]
    publisher: Optional[str]
    developer: Optional[str]
    programmer: Optional[str]
    artist: Optional[str]
    musician: Optional[str]
    genre: Optional[str]
    language: Optional[str]
    license: Optional[str]
    cracker: Optional[str]
    players_from: Optional[int]
    players_to: Optional[int]
    rating: Optional[int]
    control: Optional[str]
    version: Optional[str]
    comment: Optional[str]
    memo: Optional[str]
    weblink_name: Optional[str]
    weblink_url: Optional[str]

    @property
    def players(self):
        if not self.players_from:
            return ""
        if self.players_from == self.players_to or not self.players_to:
            return str(self.players_from)
        return f"{self.players_from}-{self.players_to}"

    @property
    def notes(self):
        return "\n\n".join(x for x in (clean(self.comment), clean(self.memo)) if x)


@dataclass(frozen=True)
class Extra:
    id: int
    name: str
    path: Optional[str]
    runnable: bool = False   # Extras.Type = 1: a zip FS-UAE can run (SPS disks, WHDLoad installs)
    data: Optional[str] = None
    file_to_run: Optional[str] = None


@dataclass(frozen=True)
class ExtraFile:
    """An Extra resolved against the data folder."""
    extra: Extra
    path: Optional[Path]

    @property
    def exists(self):
        return bool(self.path) and self.path.is_file()
