# Kickstarts

Put your Amiga Kickstart ROM dumps in this folder. They are not included in the repository, because Kickstart is copyrighted: supply your own dumps (for example from Amiga Forever or a real machine).

The file names must contain the version, like:

```
Kickstart v1.3 rev 34.5 (1987)(Commodore)(A500-A1000-A2000-CDTV).rom
Kickstart v3.1 rev 40.68 (1993)(Commodore)(A1200).rom
```

The app uses the Kickstart version a game asks for, and otherwise the closest one: games that want 2.0 or newer get the oldest ROM from 2.0 up, and games that want 1.x get the newest 1.x ROM. **Kickstart 1.3** and **3.1** cover almost everything.

Everything in this folder except this file is ignored by git.
