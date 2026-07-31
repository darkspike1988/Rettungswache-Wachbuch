# Test- und Go-live-Checkliste

Ein erfolgreicher Docker-Start ist keine fachliche, datenschutzrechtliche oder
betriebliche Freigabe.

## Technik

- [ ] CI und Anwendungstests sind gruen
- [ ] Container-Healthchecks sind gruen
- [ ] Anwendung ist nur ueber den vorgesehenen TLS-Einstieg erreichbar
- [ ] Anmeldung erfolgt nur ueber lokale Konten hinter dem vorgesehenen Proxy
- [ ] Rollenmatrix wurde mit mehreren Testkonten geprueft
- [ ] Backup wurde in einer isolierten Datenbank wiederhergestellt
- [ ] Abhaengigkeiten und Container-Images wurden gescannt
- [ ] Monitoring, Alarmierung, Patch- und Incident-Prozess sind aktiv

## Fachlichkeit

- [ ] Zweck, erlaubte Datenfelder und verantwortliche Stelle sind beschlossen
- [ ] Patienten-, Einsatz- und Gesundheitsdaten sind organisatorisch untersagt
- [ ] Rollen, Kalenderzweck und optionale Kassenregeln sind abgenommen
- [ ] Hinweise zu externen Quellen sind fachlich geprueft
- [ ] Aufbewahrungs- und Loeschfristen sind je Datenart festgelegt

## Datenschutz und Mitbestimmung

- [ ] anwendbares Datenschutz- und Mitbestimmungsrecht ist bestimmt
- [ ] Datenschutz, Informationssicherheit und Interessenvertretung sind beteiligt
- [ ] VVT, DSFA-Vorpruefung und Betroffeneninformation sind freigegeben
- [ ] Cookie-/TDDDG-Hinweis unter `/datenschutz/` ist an die Stelle angepasst
- [ ] AI-Act-Pruefung dokumentiert (Produkt ohne KI-System / kein Scoring)
- [ ] Auskunft, Berichtigung, Loeschung und Incident-Meldung sind geregelt
- [ ] Audit-Zweck und Auswertungsverbot sind dokumentiert

## Produktion

- [ ] externer Sicherheitstest oder angemessene ASVS-Pruefung ist abgeschlossen
- [ ] Betreiberangaben, Datenschutzinformation und Supportweg sind vorhanden
- [ ] Versions- und Updateprozess inkl. Rollback ist geuebt
- [ ] verschluesseltes Offsite-Backup und erfolgreicher Restore-Test existieren
- [ ] formale Go-live-Freigabe ist dokumentiert
