# Web- und Repository-Checkäquivalenz

Diese Matrix beschreibt die lokale und die schreibgeschützte CI-Abdeckung. Sie
ist ein Vertragsdokument für die Migration der alten Generatorprüfung; sie ist
kein Deployment- oder Freigabesignal.

| Bereich | Lokaler Gate | CI-Ort | Blockierende Aussage |
|---|---|---|---|
| Generator and applet | `make check-applet` | `applet`-Job | Metadaten, Schema, Python-/JavaScript-Kompilierung und Applet-Runtime bleiben in der webfreien Sparse-Auswahl abgedeckt. |
| Web contracts | `make check` plus `python3 tests/test_web_build.py` | `web`-Job | Content-, URL-, Status-, Relations- und Buildverträge werden ohne externe Schreibrechte geprüft. |
| Web artifact and budgets | `python3 tests/test_pages_artifact.py` und `python3 scripts/validate_pages_artifact.py` sowie `python3 scripts/validate_web_budgets.py` | `web`-Job: `npm --prefix web run build` | Pflichtseiten, Canonicals, Links, geheime/lokale Pfade, Symlinks und Größenlimits blockieren vor Veröffentlichung. |
| Browser and accessibility | `cd web && npm run test:browser` | `web`-Job | Benannte Browser- und Accessibility-Gates bleiben zusätzlich zum statischen Check erhalten. |
| Read-only CI policy | `python3 tests/test_check_equivalence.py` | Workflowdefinition | Pull Requests verwenden `pull_request`, lesen nur Repositoryinhalte und deployen nicht. |

Die Web-CI baut Hub und Archiv getrennt, validiert jedes Ergebnis unmittelbar
und lässt die Publish-/Pages-Jobs außerhalb dieses schreibgeschützten Checks.
