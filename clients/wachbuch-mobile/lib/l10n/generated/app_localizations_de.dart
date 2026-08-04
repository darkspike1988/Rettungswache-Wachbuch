// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for German (`de`).
class AppLocalizationsDe extends AppLocalizations {
  AppLocalizationsDe([String locale = 'de']) : super(locale);

  @override
  String get appName => 'Wachbuch';

  @override
  String errorSemanticsLabel(String message) {
    return 'Fehler: $message';
  }

  @override
  String get commonCancel => 'Abbrechen';

  @override
  String get commonSwitch => 'Wechseln';

  @override
  String get noticeSessionExpired =>
      'Ihre Anmeldung ist abgelaufen. Bitte erneut anmelden.';

  @override
  String get noticeSessionEnded => 'Sitzung beendet. Bitte erneut anmelden.';

  @override
  String get serverSwitchTitle => 'Server wechseln?';

  @override
  String serverSwitchMessage(String url) {
    return 'Ein Link möchte die App auf\n$url\numstellen. Die aktuelle Anmeldung wird dabei beendet.';
  }

  @override
  String get navOverview => 'Übersicht';

  @override
  String get navHandovers => 'Übergaben';

  @override
  String get navAccount => 'Konto';

  @override
  String get refreshTooltip => 'Aktualisieren';

  @override
  String get stationFallback => 'Wachbuch';

  @override
  String get sessionExpiredError => 'Anmeldung abgelaufen oder widerrufen.';

  @override
  String get overviewActiveHandovers => 'Aktive Übergaben';

  @override
  String get metricOpen => 'offen';

  @override
  String get metricInProgress => 'in Bearbeitung';

  @override
  String get metricUrgent => 'dringend';

  @override
  String get overviewModulesTitle => 'Module dieser Wache';

  @override
  String get overviewModulesHint =>
      'Ihre Wache und die verfügbaren Module werden automatisch aus Ihrem Benutzerkonto geladen.';

  @override
  String get moduleCalendarTitle => 'Kalender';

  @override
  String get moduleCalendarSubtitle => 'Wachentermine und Dienste';

  @override
  String get moduleCoffeeTitle => 'Kaffeekasse';

  @override
  String get moduleCoffeeSubtitle => 'Kassenstand und Buchungen';

  @override
  String get moduleChecklistsTitle => 'Checklisten';

  @override
  String get moduleChecklistsSubtitle => 'Punkte abhaken und abschließen';

  @override
  String get quickAccessTitle => 'Schnellzugriff';

  @override
  String get handoverSearchHint => 'Übergaben durchsuchen';

  @override
  String get handoverSearchClear => 'Suche löschen';

  @override
  String get filterStatus => 'Status';

  @override
  String get filterPriority => 'Priorität';

  @override
  String handoversCount(int count, int total) {
    return '$count von $total Übergaben';
  }

  @override
  String filterSectionLabel(String title) {
    return '$title filtern';
  }

  @override
  String get handoversNoneActive => 'Keine aktiven Übergaben.';

  @override
  String get handoversNoneForFilter => 'Keine Übergaben für diese Filter.';

  @override
  String get handoverUntitled => 'ohne Titel';

  @override
  String get handoverFallback => 'Übergabe';

  @override
  String handoverOpenSemantics(String title) {
    return 'Übergabe $title öffnen';
  }

  @override
  String get detailsLoadFailed => 'Details konnten nicht geladen werden.';

  @override
  String get detailsNoFurtherInfo => 'Keine weiteren Angaben.';

  @override
  String detailsUpdatedAt(String timestamp) {
    return 'Aktualisiert $timestamp';
  }

  @override
  String detailsVersion(String version) {
    return 'Version $version';
  }

  @override
  String get accountLoggedInAs => 'Angemeldet als';

  @override
  String get accountServer => 'Server';

  @override
  String get accountLicense => 'Lizenz';

  @override
  String get accountLicenseValue => 'AGPL-3.0-or-later · Quellcode offen';

  @override
  String get accountRefreshProfile => 'Profil aktualisieren';

  @override
  String get accountLogout => 'Abmelden';

  @override
  String get accountChangeServer => 'Anderen Server einrichten';

  @override
  String get kalenderTitle => 'Kalender';

  @override
  String get kalenderEmpty => 'Keine anstehenden Termine.';

  @override
  String get kalenderEntryFallback => 'Termin';

  @override
  String get kalenderTimeTbd => 'Zeit folgt';

  @override
  String get kalenderAllDay => 'Ganztägig';

  @override
  String get kaffeekasseTitle => 'Kaffeekasse';

  @override
  String get kaffeekasseBalanceLabel => 'Aktueller Kassenstand';

  @override
  String get kaffeekasseNegative =>
      'Die Kasse ist im Minus – bitte nachzahlen.';

  @override
  String get kaffeekasseLastTransactions => 'Letzte Buchungen';

  @override
  String get kaffeekasseEmptyLedger => 'Noch keine Buchungen.';

  @override
  String get kaffeekasseEntryFallback => 'Buchung';

  @override
  String get checklistenTitle => 'Checklisten';

  @override
  String get checklistenEmpty => 'Keine Checklisten verfügbar.';

  @override
  String get checklistFallback => 'Checkliste';

  @override
  String get checklistNoItems => 'Keine Punkte.';

  @override
  String get checklistCompleteButton => 'Checkliste abschließen';

  @override
  String get checklistItemFallback => 'Punkt';

  @override
  String checklistCompletedAt(String timestamp) {
    return 'Abgeschlossen $timestamp';
  }

  @override
  String get loginAppBarTitle => 'Anmelden';

  @override
  String get loginChangeServer => 'Server ändern';

  @override
  String get loginHeading => 'Anmeldung';

  @override
  String get loginTokenLabel => 'App-Token (wb_…)';

  @override
  String get loginTokenHelper =>
      'Aus dem Web unter /konto/api/ – nötig bei MFA';

  @override
  String get loginTokenRequired => 'Token erforderlich';

  @override
  String get loginUsername => 'Benutzername';

  @override
  String get loginUsernameRequired => 'Benutzername erforderlich';

  @override
  String get loginPassword => 'Passwort';

  @override
  String get loginPasswordRequired => 'Passwort erforderlich';

  @override
  String get loginShow => 'Anzeigen';

  @override
  String get loginHide => 'Verbergen';

  @override
  String get loginSubmit => 'Anmelden';

  @override
  String get loginUseCredentials => 'Mit Benutzername und Passwort';

  @override
  String get loginUseToken => 'Stattdessen App-Token nutzen';

  @override
  String get loginTokenPasteHint =>
      'Bitte App-Token einfügen (aus /konto/api/).';

  @override
  String get loginMfaHint =>
      'Bei Zwei-Faktor: App-Token im Web unter Mein Konto → App-Tokens erzeugen.';

  @override
  String get loginInvalidInput => 'Ungültige Eingabe.';

  @override
  String get setupServerAddressTitle => 'Server-Adresse Ihrer Wache';

  @override
  String get setupHint =>
      'Geben Sie die Adresse ein oder scannen Sie den QR-Code aus dem Web.';

  @override
  String get setupAddressLabel => 'Adresse';

  @override
  String get setupAddressHint => 'https://wache.example.org';

  @override
  String get setupScanQr => 'QR-Code scannen';

  @override
  String get setupAddressRequired => 'Adresse eingeben';

  @override
  String get setupAddressInvalid => 'Ungültige Adresse';

  @override
  String get setupConfirm => 'Bestätigen';

  @override
  String get setupFooter =>
      'Play-Store-Client: Verbindung nur zu Ihrem selbst gehosteten Server. Produktion: HTTPS erforderlich.';

  @override
  String get qrScanTitle => 'Server-QR scannen';

  @override
  String get qrScanCameraHint =>
      'Die Kamera wird nur zum Lesen der Server-Adresse genutzt. Es werden keine Fotos gespeichert oder hochgeladen.';

  @override
  String get qrScanInvalid => 'Kein gültiger Wachbuch-Server-QR.';

  @override
  String get qrScanWebHint =>
      'QR aus dem Wachbuch-Web unter Mein Konto → App-Tokens';

  @override
  String get qrCameraDialogTitle => 'Kamera für QR-Code';

  @override
  String get qrCameraDialogMessage =>
      'Wachbuch benötigt die Kamera ausschließlich, um den QR-Code mit der Server-Adresse Ihrer Wache zu scannen. Ohne Kamera können Sie die Adresse auch manuell eingeben.';

  @override
  String get qrCameraContinue => 'Weiter';

  @override
  String get qrCameraDeniedTitle => 'Kamera nicht freigegeben';

  @override
  String get qrCameraDeniedMessage =>
      'Ohne Kamerazugriff können Sie den QR nicht scannen. Geben Sie die Server-Adresse manuell ein oder aktivieren Sie die Kamera in den Systemeinstellungen.';

  @override
  String get qrCameraOk => 'OK';

  @override
  String get qrCameraSettings => 'Einstellungen';

  @override
  String get handoverStatusOpen => 'Offen';

  @override
  String get handoverStatusInProgress => 'In Bearbeitung';

  @override
  String get handoverStatusDone => 'Erledigt';

  @override
  String get handoverPriorityNormal => 'Normal';

  @override
  String get handoverPriorityImportant => 'Wichtig';

  @override
  String get handoverPriorityUrgent => 'Dringend';

  @override
  String get handoverCategoryStation => 'Wache';

  @override
  String get handoverCategoryVehicle => 'Fahrzeugstatus';

  @override
  String get handoverCategoryMaterial => 'Material';

  @override
  String get handoverCategoryTask => 'Offene Aufgabe';

  @override
  String get handoverCategorySafety => 'Sicherheit/Mangel';

  @override
  String get handoverEnumUnknown => 'Nicht angegeben';
}
