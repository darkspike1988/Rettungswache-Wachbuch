# Mobile-Device-Betrieb – BSI-orientierte Betreiber-Vorlage

Stand: 10. August 2026

Diese Vorlage beschreibt den Sollbetrieb von Wachbuch auf iOS-/Android-Endgeräten. Sie orientiert sich an den Prinzipien des BSI-Mindeststandards Mobile Device Management und ersetzt keine organisationsspezifische Sicherheitsrichtlinie.

## 1. Geräteklassen

Der Betreiber legt fest:

- [ ] ausschließlich dienstlich verwaltete Geräte
- [ ] COPE (Corporate Owned, Personally Enabled)
- [ ] BYOD nur nach dokumentierter Risikoentscheidung und technischer Trennung
- [ ] sonstiges Modell: `[ausfüllen]`

Für Geräte mit erhöhtem Schutzbedarf ist eine zentrale Verwaltung per MDM/UEM vorzusehen.

## 2. Mindestanforderungen

Produktiv zugelassene Geräte müssen mindestens:

- vom Hersteller noch Sicherheitsupdates erhalten,
- einen Gerätesperrcode besitzen,
- automatische oder zentral gesteuerte Sicherheitsupdates erhalten,
- Gerätespeicherverschlüsselung des Betriebssystems aktiviert haben,
- nicht gerootet/jailbroken sein,
- App-Installationen nur aus freigegebenen Quellen erlauben,
- Bildschirmsperre nach angemessener Inaktivität aktivieren,
- Verlust-/Diebstahlprozess und – bei verwalteten Geräten – Remote-Sperrung/-Löschung unterstützen.

## 3. MDM/UEM-Sollrichtlinien

Soweit technisch verfügbar und dem Schutzbedarf angemessen:

- Mindest-OS-Version erzwingen,
- kompromittierte/rooted/jailbroken Geräte sperren,
- Gerätesperrcode-/Biometrie-Richtlinie erzwingen,
- automatische Sperrzeit begrenzen,
- Wachbuch als verwaltete App verteilen,
- App-Konfiguration/Server-URL kontrolliert verteilen, falls genutzt,
- Copy/Paste-/Open-in-Regeln für sensible Organisationsdaten festlegen,
- verwaltete Backups kontrollieren,
- Screenshots/Bildschirmaufzeichnung bei erhöhtem Schutzbedarf einschränken,
- Remote-Wipe und selektives Löschen verwalteter App-Daten ermöglichen,
- Compliance-Status regelmäßig prüfen.

## 4. Wachbuch-spezifische Daten

Der Mobile Client speichert nach Produktkonzept:

- Serveradresse lokal,
- App-Token und Ablaufzeit im Betriebssystem-Secure-Storage,
- server-/tokengebundene Offline-Lesesnapshots im Secure-Storage,
- lokale, nicht für Tracking bestimmte App-Einstellungen.

Produktive Android-Builds deaktivieren Cleartext-Verkehr und App-Backups. Bei Logout/Serverwechsel werden Token und zugehöriger Offline-Cache entfernt.

## 5. Mängelfotos

- nur sachbezogene Mängel fotografieren,
- keine Patienten, Einsatzunterlagen, Dienstpläne, Bildschirme mit Personendaten oder sonstige sachfremde Personen aufnehmen,
- Client soll ausgewählte Bilder vor Upload in ein neues JPEG ohne Quell-Metadaten/EXIF/GPS neu codieren,
- Kamera-/Fotorechte nur bei Bedarf erteilen,
- lokale Galerie-/Kamera-Kopien unterliegen zusätzlich der Geräte-/MDM-Richtlinie.

## 6. Verlust oder Diebstahl

Unverzüglich:

1. IT/Service Desk und zuständige Führung melden,
2. Gerät über MDM sperren bzw. löschen,
3. Wachbuch-App-Token serverseitig widerrufen,
4. weitere Geräte-/SSO-/VPN-Zugänge prüfen,
5. Umfang möglicher Offline-Daten bewerten,
6. Datenschutz-/Security-Incident-Prozess starten,
7. Art. 33/34 DSGVO durch Verantwortliche/Datenschutz prüfen lassen,
8. Ereignis und Maßnahmen dokumentieren.

## 7. Gerätewechsel / Ausscheiden

- App-Token widerrufen,
- aus Wachbuch abmelden,
- verwaltete App-Daten löschen,
- Gerät bei Rückgabe vollständig gemäß MDM-/Asset-Prozess zurücksetzen,
- alte Gerätebindung/Push-Abos prüfen,
- keine Produktionsdaten auf privaten Ersatzgeräten übertragen.

## 8. App-Updates

- Store-/MDM-Verteilung aus freigegebenem Release,
- kritische Security-Updates priorisiert ausrollen,
- keine ungeprüften APK-/IPA-Dateien per Messenger/Mail verteilen,
- unterstützte Mindestversion festlegen,
- bei sicherheitsrelevanten Storage-/Krypto-Migrationen stufenweise Pilot → Rollout → Nachkontrolle durchführen.

## 9. Test- und Demo-Geräte

- keine Produktivtokens/Echtdaten in Screenshots oder Demo-Geräten,
- separate Review-/Demo-Server verwenden,
- Debug-Builds mit unsicherem LAN-HTTP niemals als Produktivbuild verteilen,
- Testgeräte nach Testende bereinigen.

## 10. Regelmäßige Kontrolle

- MDM-/Compliance-Review: `[Intervall]`
- Mindest-OS-Version Review: `[Intervall]`
- Gerätebestand/Owner Review: `[Intervall]`
- Wachbuch-Mindestversion: `[Version]`
- Verlust-/Remote-Wipe-Test: `[Intervall]`

Freigabe IT/Informationssicherheit: `[Name/Datum]`  
Freigabe Datenschutz: `[Name/Datum]`
