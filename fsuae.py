"""Finding FS-UAE, preparing floppy images / WHDLoad drives and launching games."""
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

from config import Config
from data_layout import DataLayout

# FS-UAE joystick_port_1 devices. Port 0 always gets the mouse.
CONTROLLERS = {"keyboard": ("Keyboard (FS-UAE keyboard joystick)", "keyboard"),
               "joystick": ("Real joystick / gamepad", "joystick")}
DEFAULT_CONTROLLER = "keyboard"

FLOPPY_EXTS = (".adf", ".adz", ".dms", ".ipf")  # in order of preference
MAX_DRIVES = 4
MAX_SWAP_IMAGES = 20  # FS-UAE floppy_image_0 .. floppy_image_19
DISK_ZIP = re.compile(r"^(?P<base>.+)_Disk(?P<disk>\w+)\.zip$", re.I)
KICKSTART_NAME = re.compile(r"kickstart\D*v?(\d)\.(\d+)", re.I)
VERSION = re.compile(r"(\d)\.(\d+)")

# Order the launch choices are offered in: WHDLoad installs first (they need no disk swapping),
# then the game's own disks, then the SPS (IPF) disks.
RANK = {"whd": 0, "game": 1, "sps": 2}


def load_controller_settings(config: Config):
    """(controller, fullscreen, scanlines, extra_args) from config.json, with defaults filled in."""
    controller = config.get("controller", DEFAULT_CONTROLLER)
    if controller not in CONTROLLERS:
        controller = DEFAULT_CONTROLLER
    return (controller, bool(config.get("fullscreen", True)), bool(config.get("scanlines", True)),
            str(config.get("fsuae_args", "") or ""))


class LaunchError(Exception):
    """Raised when a game cannot be launched; the message is user-facing."""


# ---------- the WinUAE-style configuration stored in the database ----------

def parse_config(text):
    """`key=value` lines -> dict (lower-case keys). Anything else is ignored."""
    cfg = {}
    for line in (text or "").splitlines():
        if "=" in line and not line.lstrip().startswith(("[", ";", "#")):
            key, value = line.split("=", 1)
            cfg[key.strip().lower()] = value.strip()
    return cfg


def extra_config_text(data):
    """Extras.Data holds ten `|~|`-separated fields; the 8th is the same kind of config text."""
    fields = (data or "").split("|~|")
    return fields[7] if len(fields) > 7 else ""


def _int(cfg, key, default=0):
    try:
        return int(float(cfg.get(key, default)))
    except (TypeError, ValueError):
        return default


class Kickstarts:
    """The Kickstart ROMs found in emulator/Kickstarts, picked by version."""

    def __init__(self, folder):
        self.roms = []  # (version, path)
        folder = Path(folder)
        if folder.is_dir():
            for p in sorted(folder.iterdir()):
                m = KICKSTART_NAME.search(p.name)
                if p.is_file() and p.suffix.lower() in (".rom", ".bin") and m:
                    self.roms.append((float(f"{m.group(1)}.{m.group(2)}"), p))

    @staticmethod
    def wanted_version(text):
        m = VERSION.search(text or "")
        return float(f"{m.group(1)}.{m.group(2)}") if m else 1.3

    def pick(self, wanted):
        """Best ROM for a `kickstart_rom` value such as 'v1.3', 'v2.05' or 'v3.1 A1200'.
        Exact version if present; otherwise a 2.x/3.x game gets the oldest ROM that is 2.0
        or newer and a 1.x game gets the newest 1.x ROM, falling back to whatever exists."""
        if not self.roms:
            return None
        want = self.wanted_version(wanted)
        for version, path in self.roms:
            if abs(version - want) < 0.001:
                return path
        newer = sorted((v, p) for v, p in self.roms if v >= 2.0)
        older = sorted((v, p) for v, p in self.roms if v < 2.0)
        if want >= 2.0:
            order = newer[:1] + older[-1:]
        else:
            order = older[-1:] + newer[:1]
        return order[0][1]


def fsuae_options(cfg, kickstarts: Kickstarts, whd=False):
    """FS-UAE options (name -> value) for a game's WinUAE-style `cfg` dict."""
    chipset = cfg.get("chipset", "OCS").upper()
    chip = _int(cfg, "chipmem_size", 1) * 512      # WinUAE: units of 512 KB
    slow = _int(cfg, "bogomem_size", 0) * 256      # units of 256 KB
    fast = _int(cfg, "fastmem_size", 0) * 1024     # MB
    if whd or chipset == "AGA" or _int(cfg, "cpu_model", 68000) >= 68020:
        model = "A1200"
    elif chipset.startswith("ECS") or chip > 512:
        model = "A500+"
    else:
        model = "A500"
    if whd:
        chip, slow, fast = 2048, 0, 8192  # roomy: WHDLoad slaves take what they need
    options = {"amiga_model": model,
               "chip_memory": str(min(chip, 2048)),
               "slow_memory": str(slow if slow in (0, 256, 512, 1024, 1792) else 512),
               "fast_memory": str(fast)}
    if model == "A1200":
        options["slow_memory"] = "0"
    if cfg.get("ntsc", "").lower() == "true":
        options["ntsc_mode"] = "1"
    rom = kickstarts.pick("v3.1 A1200" if whd else cfg.get("kickstart_rom") or cfg.get("ickstart_rom"))  # sic: typo in 2 rows
    if rom:
        options["kickstart_file"] = str(rom)
    return options


# ---------- finding the emulator ----------

class FsuaeLocator:
    def __init__(self, layout: DataLayout, config: Config):
        self.layout = layout
        self.config = config

    @staticmethod
    def normalize(p):
        """Accept FS-UAE.app or the folder holding fs-uae(.exe) and return the executable."""
        p = Path(p)
        if p.suffix == ".app":
            p = p / "Contents" / "MacOS" / "fs-uae"
        elif p.is_dir():
            for sub in ("", "Windows/x86-64", "Windows/x86", "Linux/x86-64", "bin"):
                for name in ("fs-uae.exe", "fs-uae"):
                    if (p / sub / name).is_file():
                        return p / sub / name
        return p

    def find(self):
        """Locate FS-UAE: env var, saved setting, emulator/ folder, PATH, usual places."""
        emu = self.layout.emulator_dir
        candidates = [os.environ.get("FSUAE_PATH"), self.config.get("fsuae"),
                      emu / "FS-UAE.app", emu, shutil.which("fs-uae"),
                      "/Applications/FS-UAE.app", "/opt/homebrew/bin/fs-uae",
                      "/usr/local/bin/fs-uae", "/usr/bin/fs-uae",
                      r"C:\Program Files\FS-UAE\fs-uae.exe"]
        for c in candidates:
            if c and self.normalize(c).is_file():
                return self.normalize(c)
        return None

    def remember(self, path):
        """Validate and persist a user-chosen executable; returns it or None."""
        exe = self.normalize(path)
        if not exe.is_file():
            return None
        self.config.set("fsuae", str(exe))
        return exe


# ---------- what can be launched ----------

@dataclass(frozen=True)
class LaunchOption:
    label: str
    kind: str                    # "whd" (WHDLoad install) or "floppy" (disk images in a zip)
    zip_path: Path
    config_text: Optional[str]   # WinUAE-style settings from the database
    file_to_run: Optional[str]
    rank: int = 1


class LaunchPlanner:
    """Lists the ways a game can be started, from the files present in the data folder."""

    def __init__(self, layout: DataLayout, repo):
        self.layout, self.repo = layout, repo

    def options(self, game):
        found = []
        game_zip = self.layout.game_file(game.filename)
        if game_zip and game_zip.is_file():
            found.append(LaunchOption(f"Game disk: {game_zip.name}", "floppy", game_zip,
                                      self.repo.game_config(game.id),
                                      self.repo.file_to_run(game.id), RANK["game"]))
        for extra in self.repo.extras(game.id):
            path = self.layout.extra(extra.path) if extra.runnable else None
            if path and path.is_file():
                found.append(self.extra_option(extra, path))
        return sorted(found, key=lambda o: o.rank)

    @staticmethod
    def extra_option(extra, path):
        """The LaunchOption for one runnable Extra (SPS disks or a WHDLoad install)."""
        whd = extra.name.lower().startswith("whd")
        return LaunchOption(f"{extra.name}: {path.name}", "whd" if whd else "floppy", path,
                            extra_config_text(extra.data), extra.file_to_run,
                            RANK["whd" if whd else "sps"])


# ---------- preparing the files ----------

def _safe_extract(z: zipfile.ZipFile, dest: Path):
    """Extract a whole zip into `dest`, refusing paths that would leave it."""
    root = dest.resolve()
    for info in z.infolist():
        name = info.filename
        if name.startswith("__MACOSX") or name.endswith(".DS_Store"):
            continue
        rel = PurePosixPath(name)
        target = (dest / Path(*rel.parts)).resolve() if rel.parts else root
        if target != root and root not in target.parents:
            continue
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out)


class DiskPreparer:
    """Unpacks floppy images from game zips and builds WHDLoad drives under data/cache/run/<id>."""

    def __init__(self, layout: DataLayout):
        self.layout = layout

    def run_dir(self, ga_id):
        d = self.layout.cache / "run" / str(ga_id)
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        return d

    @staticmethod
    def sibling_zips(zip_path: Path):
        """Other disks of the same game: 'Name_Disk2.zip' sits next to 'Name_Disk1.zip'."""
        m = DISK_ZIP.match(zip_path.name)
        if not m:
            return []
        base = m.group("base").casefold()
        found = []
        for p in zip_path.parent.iterdir():
            n = DISK_ZIP.match(p.name)
            if n and p != zip_path and n.group("base").casefold() == base:
                found.append((n.group("disk").casefold(), p))
        return [p for _disk, p in sorted(found)]

    @staticmethod
    def _images(z: zipfile.ZipFile, file_to_run):
        members = [i for i in z.infolist() if not i.is_dir()]
        images = sorted((i for i in members if Path(i.filename).suffix.lower() in FLOPPY_EXTS),
                        key=lambda i: (Path(i.filename).suffix.lower() != ".adf", i.filename.lower()))
        if file_to_run:
            want = Path(file_to_run.replace("\\", "/")).name.lower()
            first = [i for i in images if Path(i.filename).name.lower() == want]
            images = first + [i for i in images if i not in first]
        return images

    def floppies(self, ga_id, zip_path, file_to_run):
        """Extract the disk image(s) of `zip_path` (and of the other disks of the same game).
        Returns the image paths, the selected zip's first. Extracting by basename only
        avoids any path-traversal from zip entries."""
        run_dir = self.run_dir(ga_id)
        disks = []
        for n, zp in enumerate([zip_path, *self.sibling_zips(zip_path)]):
            with zipfile.ZipFile(zp) as z:
                images = self._images(z, file_to_run if n == 0 else None)
                if n == 0 and not images:
                    raise ValueError("No disk image (.adf/.dms/.ipf/...) found in the zip.")
                for info in images:
                    target_dir = run_dir / f"disk{n}"
                    target_dir.mkdir(exist_ok=True)
                    target = target_dir / Path(info.filename).name
                    with z.open(info) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    disks.append(target)
        return disks[:MAX_SWAP_IMAGES]

    def whdload(self, ga_id, zip_path, cfg):
        """Build DH0 (the WHDLoad boot drive with a generated user-startup) and DH1 (the game
        zip's contents). Returns (dh0, dh1)."""
        if not (self.layout.whd_dir / "C" / "WHDLoad").is_file():
            raise ValueError(f"The WHDLoad files are missing:\n{self.layout.whd_dir}\n\n"
                             "Run Populate folders with WHD.rar in the sources folder.")
        cd, load = cfg.get("cd"), cfg.get("whdload")
        if not (cd and load):
            raise ValueError("The database has no WHDLoad start command for this game.")
        run_dir = self.run_dir(ga_id)
        dh0, dh1 = run_dir / "dh0", run_dir / "dh1"
        shutil.copytree(self.layout.whd_dir, dh0)
        dh1.mkdir()
        with zipfile.ZipFile(zip_path) as z:
            _safe_extract(z, dh1)
        startup = dh0 / "S" / "user-startup"
        startup.parent.mkdir(exist_ok=True)
        startup.write_text(
            'echo ""\n'
            'echo "GamebaseAmiga :: WHDLoad"\n'
            f'echo "Running: {load.split(";")[0].split()[0]}"\n'
            'echo ""\n'
            f"cd {cd}\n"
            f"whdload {load}\n", encoding="latin-1", errors="replace")
        return dh0, dh1


class FsuaeLauncher:
    def __init__(self, layout: DataLayout, preparer: DiskPreparer, config: Config):
        self.layout = layout
        self.preparer = preparer
        self.config = config  # controller, display settings and extra arguments are read on every launch

    def _write_config(self, run_dir, options):
        conf = run_dir / "game.fs-uae"
        lines = ["[fs-uae]"] + [f"{k} = {v}" for k, v in options.items()]
        conf.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return conf

    def build_options(self, game, option: LaunchOption):
        """Prepare the files and return (run_dir, FS-UAE options)."""
        cfg = parse_config(option.config_text)
        kickstarts = Kickstarts(self.layout.kickstarts)
        options = fsuae_options(cfg, kickstarts, whd=option.kind == "whd")
        if "kickstart_file" not in options:
            raise LaunchError(f"No Kickstart ROM found in:\n{self.layout.kickstarts}\n\n"
                              "Put your Kickstart ROM files there.")
        controller, fullscreen, scanlines, _extra = load_controller_settings(self.config)
        options["fullscreen"] = "1" if fullscreen else "0"
        options["scanlines"] = "1" if scanlines else "0"
        options["joystick_port_0"] = "mouse"
        options["joystick_port_1"] = CONTROLLERS[controller][1]
        if option.kind == "whd":
            dh0, dh1 = self.preparer.whdload(game.id, option.zip_path, cfg)
            options.update({"hard_drive_0": dh0.as_posix(), "hard_drive_0_label": "DH0",
                            "hard_drive_1": dh1.as_posix(), "hard_drive_1_label": "DH1"})
            return dh0.parent, options
        disks = self.preparer.floppies(game.id, option.zip_path, option.file_to_run)
        drives = min(max(len(disks), _int(cfg, "nr_floppies", 1)), MAX_DRIVES)
        options["floppy_drive_count"] = str(drives)
        for n, disk in enumerate(disks[:drives]):
            options[f"floppy_drive_{n}"] = disk.as_posix()
        for n, disk in enumerate(disks):
            options[f"floppy_image_{n}"] = disk.as_posix()
        return disks[0].parent.parent, options

    def launch(self, fsuae, game, option: LaunchOption):
        try:
            run_dir, options = self.build_options(game, option)
        except (zipfile.BadZipFile, ValueError, OSError) as e:
            raise LaunchError(f"{game.name}\n\n{e}") from e
        conf = self._write_config(run_dir, options)
        _controller, _fullscreen, _scanlines, extra = load_controller_settings(self.config)
        cmd = [str(fsuae), str(conf), *extra.split()]
        try:
            subprocess.Popen(cmd, cwd=run_dir)
        except OSError as e:
            raise LaunchError(str(e)) from e
