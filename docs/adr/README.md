# Architekturentscheidungen

Autorität: V2-Kapitel 20 des kanonischen Plans (SHA-256 `09294f9206bf6b35242e133caa619a931e92bb2118e1fef55ad02b86a5a4237a`). Historisches Kapitel 37 mit 13 Entwürfen ist bei Konflikten superseded; IDs 001–013 sind historische Kernmenge, 001–015 aktuelle Menge.

| ADR | Entscheidung | Status | Neubewertungstrigger |
| --- | --- | --- | --- |
| `ADR-WEB-001` | statischer Astro-7-Output | angenommen/implementiert | Buildzeit oder Archivgröße überschreitet Reserve |
| `ADR-WEB-002` | Factory im Generatorrepo, dünne nummerierte Archive | angenommen/implementiert | unabhängige Archivwartung wird unmöglich |
| `ADR-WEB-003` | Originale/Derivate in GitHub Releases, nicht im Git-Hauptbaum | angenommen/implementiert | Release-/Transfergrenzen oder Kosten untragbar |
| `ADR-WEB-004` | Sharp/libvips für Webderivate | angenommen/implementiert | reproduzierbare Sicherheits-/Plattformprobleme |
| `ADR-WEB-005` | zehn Storys je Buch, fünf Bücher/50 Storys je Archiv | angenommen/implementiert | Nutzer-/Performanceevidenz verlangt andere Grenze |
| `ADR-WEB-006` | unveränderlicher Factory-SHA je Archiv | angenommen/implementiert | niemals auf bewegliches `main` wechseln |
| `ADR-WEB-007` | statische Pagination statt unkontrolliertem Infinite Scroll | angenommen/implementiert | Browsermessung zeigt klare bessere Alternative |
| `ADR-WEB-008` | sichere Markdownpipeline mit Sanitizing | angenommen/implementiert | kein ungeprüftes Raw HTML |
| `ADR-WEB-009` | lokale Zustände ohne Konto/Tracking | angenommen, unvollständig | M03-Schemafreeze |
| `ADR-WEB-010` | Custom Domains im `telacore.org`-Namensraum | Soll umgesetzt, extern zu prüfen | DNS-/HTTPS-/Domainproblem |
| `ADR-WEB-011` | Suche nicht Teil des Kern-MVP | angenommen | Storymenge und Nutzerbedarf belegen Nutzen |
| `ADR-WEB-012` | Meta-CSP auf Pages plus keine fremden Origins | teilweise | vorgeschaltete Plattform erlaubt echte Header |
| `ADR-WEB-013` | Kapitelpermalinks zusätzlich zur Vollbandansicht | **offen M02** | vor Reader-PR einfrieren |
| `ADR-WEB-014` | Build und Deploy als getrennte Jobs | **empfohlen M01** | vor Factory-Stabilisierung entscheiden |
| `ADR-WEB-015` | Repin nur nach vollständigem Profil-/Live-Nachweis | **empfohlen M01** | gilt für jedes Archiv dauerhaft |
