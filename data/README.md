# Data folder

The app reads the game files from this folder (the default *data folder*). The files are not included in the repository. Use **Populate folders…** in the app to extract them from the GameBase Amiga v2.3 source archives, which you can download from <https://archive.org/details/Gamebase_Amiga_v2.3>.

The sub-folders are created when you populate:

```
games/              game zips, one folder per initial (0, A … Z)
screenshots/        in-game screenshots (same sub-folders)
music/              zipped music modules (same sub-folders)
extras/             Instructions, Hints, Cover Scans, MP3…
extras_runnable/    extras that can run in the emulator (SPS, WHDLoad)
whd/                the WHDLoad boot drive (C, Devs, Libs, S)
covers/             optional generated front covers ({GA_Id}.jpg)
cache/              temporary disk images and drives created at launch
```

You can point the app at a different data folder in **Settings…**.
