# Web-Mediensicherheit

Die versionierte Policy in `config/web-media-limits.json` begrenzt Originale auf 25 MiB und 50 Millionen
Pixel. Die Inventur prüft diese Grenzen vor einer vollständigen Verarbeitung, erkennt ungültige Header/EOF,
Pillow-Dekompressionsbomben, LFS-Pointer, Format-/Suffixabweichungen, Symlinks und portable
Case-Kollisionen. Ein Fehler stoppt den Datensatz und erzeugt keinen gültigen Teilrelease.

Beim Derivat wird EXIF-Orientierung zuerst angewendet. Danach wird ein neues RGB-Bild erzeugt und ohne EXIF-,
GPS-, ICC- oder sonstige Quellmetadaten als WebP gespeichert. Die Originaldatei bleibt unverändert und wird
als eigenes, hashgebundenes Releaseasset behandelt.

Die zentralen Negativ- und Sicherheitsprüfungen liegen in `tests/platform/test_media_release.py` und werden
über den bestehenden Plattformtestlauf in `make check` ausgeführt. Fehlerberichte verwenden relative
Medienpfade; lokale absolute Quellpfade werden nicht nach außen gegeben.
