# Emulator folder

Place the FS-UAE emulator here, for example `FS-UAE.app` on macOS. The app looks in this folder first (after `FSUAE_PATH` and the saved setting), so you do not need to install FS-UAE system-wide. Download it from <https://fs-uae.net/>.

`Portable.ini` is part of the repository. With it next to FS-UAE, the emulator starts in portable mode: it keeps its own working folders (`Cache`, `Configurations`, `Save States`…) in this folder instead of your home folder. Keep that file when you update FS-UAE.

Also needed:

- `Kickstarts/`: your own Kickstart ROMs, see the README in that folder.
- `System/CAPSImg/`: the optional *capsimg* plugin for `.ipf` (SPS) disks, see the main README.
