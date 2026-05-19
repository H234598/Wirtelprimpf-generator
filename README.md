# Katzenbilder

Dieses Repository sammelt generierte Katzenbilder und die dazugehoerigen
Prompt-Dateien.

## Ordner

- `Wirtelprimpf/`: generierte Wirtelprimpf-Bilder und die verwendeten Prompts.
- `Sourcecode/`: generalisierter Generator-Code, Installationshinweise,
  Environment-Beispiel und optionale systemd-User-Units.

## Secrets

OpenAI API-Keys gehoeren nicht in dieses Repository. Der Generator liest den
Key aus einer privaten lokalen Environment-Datei, siehe
`Sourcecode/README.md`.

## Automatisierung

Der Generator kann lokal manuell ausgefuehrt oder ueber einen systemd-User-Timer
stuendlich gestartet werden. Die portable Referenzimplementierung liegt unter
`Sourcecode/`.
