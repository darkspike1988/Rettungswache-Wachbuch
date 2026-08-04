import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_de.dart';
import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('de'),
    Locale('en'),
  ];

  /// No description provided for @appName.
  ///
  /// In de, this message translates to:
  /// **'Wachbuch'**
  String get appName;

  /// No description provided for @errorSemanticsLabel.
  ///
  /// In de, this message translates to:
  /// **'Fehler: {message}'**
  String errorSemanticsLabel(String message);

  /// No description provided for @commonCancel.
  ///
  /// In de, this message translates to:
  /// **'Abbrechen'**
  String get commonCancel;

  /// No description provided for @commonSwitch.
  ///
  /// In de, this message translates to:
  /// **'Wechseln'**
  String get commonSwitch;

  /// No description provided for @noticeSessionExpired.
  ///
  /// In de, this message translates to:
  /// **'Ihre Anmeldung ist abgelaufen. Bitte erneut anmelden.'**
  String get noticeSessionExpired;

  /// No description provided for @noticeSessionEnded.
  ///
  /// In de, this message translates to:
  /// **'Sitzung beendet. Bitte erneut anmelden.'**
  String get noticeSessionEnded;

  /// No description provided for @serverSwitchTitle.
  ///
  /// In de, this message translates to:
  /// **'Server wechseln?'**
  String get serverSwitchTitle;

  /// No description provided for @serverSwitchMessage.
  ///
  /// In de, this message translates to:
  /// **'Ein Link möchte die App auf\n{url}\numstellen. Die aktuelle Anmeldung wird dabei beendet.'**
  String serverSwitchMessage(String url);

  /// No description provided for @navOverview.
  ///
  /// In de, this message translates to:
  /// **'Übersicht'**
  String get navOverview;

  /// No description provided for @navHandovers.
  ///
  /// In de, this message translates to:
  /// **'Übergaben'**
  String get navHandovers;

  /// No description provided for @navAccount.
  ///
  /// In de, this message translates to:
  /// **'Konto'**
  String get navAccount;

  /// No description provided for @refreshTooltip.
  ///
  /// In de, this message translates to:
  /// **'Aktualisieren'**
  String get refreshTooltip;

  /// No description provided for @stationFallback.
  ///
  /// In de, this message translates to:
  /// **'Wachbuch'**
  String get stationFallback;

  /// No description provided for @sessionExpiredError.
  ///
  /// In de, this message translates to:
  /// **'Anmeldung abgelaufen oder widerrufen.'**
  String get sessionExpiredError;

  /// No description provided for @overviewActiveHandovers.
  ///
  /// In de, this message translates to:
  /// **'Aktive Übergaben'**
  String get overviewActiveHandovers;

  /// No description provided for @metricOpen.
  ///
  /// In de, this message translates to:
  /// **'offen'**
  String get metricOpen;

  /// No description provided for @metricInProgress.
  ///
  /// In de, this message translates to:
  /// **'in Bearbeitung'**
  String get metricInProgress;

  /// No description provided for @metricUrgent.
  ///
  /// In de, this message translates to:
  /// **'dringend'**
  String get metricUrgent;

  /// No description provided for @overviewModulesTitle.
  ///
  /// In de, this message translates to:
  /// **'Module dieser Wache'**
  String get overviewModulesTitle;

  /// No description provided for @overviewModulesHint.
  ///
  /// In de, this message translates to:
  /// **'Ihre Wache und die verfügbaren Module werden automatisch aus Ihrem Benutzerkonto geladen.'**
  String get overviewModulesHint;

  /// No description provided for @moduleCalendarTitle.
  ///
  /// In de, this message translates to:
  /// **'Kalender'**
  String get moduleCalendarTitle;

  /// No description provided for @moduleCalendarSubtitle.
  ///
  /// In de, this message translates to:
  /// **'Wachentermine und Dienste'**
  String get moduleCalendarSubtitle;

  /// No description provided for @moduleCoffeeTitle.
  ///
  /// In de, this message translates to:
  /// **'Kaffeekasse'**
  String get moduleCoffeeTitle;

  /// No description provided for @moduleCoffeeSubtitle.
  ///
  /// In de, this message translates to:
  /// **'Kassenstand und Buchungen'**
  String get moduleCoffeeSubtitle;

  /// No description provided for @moduleChecklistsTitle.
  ///
  /// In de, this message translates to:
  /// **'Checklisten'**
  String get moduleChecklistsTitle;

  /// No description provided for @moduleChecklistsSubtitle.
  ///
  /// In de, this message translates to:
  /// **'Punkte abhaken und abschließen'**
  String get moduleChecklistsSubtitle;

  /// No description provided for @quickAccessTitle.
  ///
  /// In de, this message translates to:
  /// **'Schnellzugriff'**
  String get quickAccessTitle;

  /// No description provided for @handoverSearchHint.
  ///
  /// In de, this message translates to:
  /// **'Übergaben durchsuchen'**
  String get handoverSearchHint;

  /// No description provided for @handoverSearchClear.
  ///
  /// In de, this message translates to:
  /// **'Suche löschen'**
  String get handoverSearchClear;

  /// No description provided for @filterStatus.
  ///
  /// In de, this message translates to:
  /// **'Status'**
  String get filterStatus;

  /// No description provided for @filterPriority.
  ///
  /// In de, this message translates to:
  /// **'Priorität'**
  String get filterPriority;

  /// No description provided for @handoversCount.
  ///
  /// In de, this message translates to:
  /// **'{count} von {total} Übergaben'**
  String handoversCount(int count, int total);

  /// No description provided for @filterSectionLabel.
  ///
  /// In de, this message translates to:
  /// **'{title} filtern'**
  String filterSectionLabel(String title);

  /// No description provided for @handoversNoneActive.
  ///
  /// In de, this message translates to:
  /// **'Keine aktiven Übergaben.'**
  String get handoversNoneActive;

  /// No description provided for @handoversNoneForFilter.
  ///
  /// In de, this message translates to:
  /// **'Keine Übergaben für diese Filter.'**
  String get handoversNoneForFilter;

  /// No description provided for @handoverUntitled.
  ///
  /// In de, this message translates to:
  /// **'ohne Titel'**
  String get handoverUntitled;

  /// No description provided for @handoverFallback.
  ///
  /// In de, this message translates to:
  /// **'Übergabe'**
  String get handoverFallback;

  /// No description provided for @handoverOpenSemantics.
  ///
  /// In de, this message translates to:
  /// **'Übergabe {title} öffnen'**
  String handoverOpenSemantics(String title);

  /// No description provided for @detailsLoadFailed.
  ///
  /// In de, this message translates to:
  /// **'Details konnten nicht geladen werden.'**
  String get detailsLoadFailed;

  /// No description provided for @detailsNoFurtherInfo.
  ///
  /// In de, this message translates to:
  /// **'Keine weiteren Angaben.'**
  String get detailsNoFurtherInfo;

  /// No description provided for @detailsUpdatedAt.
  ///
  /// In de, this message translates to:
  /// **'Aktualisiert {timestamp}'**
  String detailsUpdatedAt(String timestamp);

  /// No description provided for @detailsVersion.
  ///
  /// In de, this message translates to:
  /// **'Version {version}'**
  String detailsVersion(String version);

  /// No description provided for @accountLoggedInAs.
  ///
  /// In de, this message translates to:
  /// **'Angemeldet als'**
  String get accountLoggedInAs;

  /// No description provided for @accountServer.
  ///
  /// In de, this message translates to:
  /// **'Server'**
  String get accountServer;

  /// No description provided for @accountLicense.
  ///
  /// In de, this message translates to:
  /// **'Lizenz'**
  String get accountLicense;

  /// No description provided for @accountLicenseValue.
  ///
  /// In de, this message translates to:
  /// **'AGPL-3.0-or-later · Quellcode offen'**
  String get accountLicenseValue;

  /// No description provided for @accountRefreshProfile.
  ///
  /// In de, this message translates to:
  /// **'Profil aktualisieren'**
  String get accountRefreshProfile;

  /// No description provided for @accountLogout.
  ///
  /// In de, this message translates to:
  /// **'Abmelden'**
  String get accountLogout;

  /// No description provided for @accountChangeServer.
  ///
  /// In de, this message translates to:
  /// **'Anderen Server einrichten'**
  String get accountChangeServer;

  /// No description provided for @kalenderTitle.
  ///
  /// In de, this message translates to:
  /// **'Kalender'**
  String get kalenderTitle;

  /// No description provided for @kalenderEmpty.
  ///
  /// In de, this message translates to:
  /// **'Keine anstehenden Termine.'**
  String get kalenderEmpty;

  /// No description provided for @kalenderEntryFallback.
  ///
  /// In de, this message translates to:
  /// **'Termin'**
  String get kalenderEntryFallback;

  /// No description provided for @kalenderTimeTbd.
  ///
  /// In de, this message translates to:
  /// **'Zeit folgt'**
  String get kalenderTimeTbd;

  /// No description provided for @kalenderAllDay.
  ///
  /// In de, this message translates to:
  /// **'Ganztägig'**
  String get kalenderAllDay;

  /// No description provided for @kaffeekasseTitle.
  ///
  /// In de, this message translates to:
  /// **'Kaffeekasse'**
  String get kaffeekasseTitle;

  /// No description provided for @kaffeekasseBalanceLabel.
  ///
  /// In de, this message translates to:
  /// **'Aktueller Kassenstand'**
  String get kaffeekasseBalanceLabel;

  /// No description provided for @kaffeekasseNegative.
  ///
  /// In de, this message translates to:
  /// **'Die Kasse ist im Minus – bitte nachzahlen.'**
  String get kaffeekasseNegative;

  /// No description provided for @kaffeekasseLastTransactions.
  ///
  /// In de, this message translates to:
  /// **'Letzte Buchungen'**
  String get kaffeekasseLastTransactions;

  /// No description provided for @kaffeekasseEmptyLedger.
  ///
  /// In de, this message translates to:
  /// **'Noch keine Buchungen.'**
  String get kaffeekasseEmptyLedger;

  /// No description provided for @kaffeekasseEntryFallback.
  ///
  /// In de, this message translates to:
  /// **'Buchung'**
  String get kaffeekasseEntryFallback;

  /// No description provided for @checklistenTitle.
  ///
  /// In de, this message translates to:
  /// **'Checklisten'**
  String get checklistenTitle;

  /// No description provided for @checklistenEmpty.
  ///
  /// In de, this message translates to:
  /// **'Keine Checklisten verfügbar.'**
  String get checklistenEmpty;

  /// No description provided for @checklistFallback.
  ///
  /// In de, this message translates to:
  /// **'Checkliste'**
  String get checklistFallback;

  /// No description provided for @checklistNoItems.
  ///
  /// In de, this message translates to:
  /// **'Keine Punkte.'**
  String get checklistNoItems;

  /// No description provided for @checklistCompleteButton.
  ///
  /// In de, this message translates to:
  /// **'Checkliste abschließen'**
  String get checklistCompleteButton;

  /// No description provided for @checklistItemFallback.
  ///
  /// In de, this message translates to:
  /// **'Punkt'**
  String get checklistItemFallback;

  /// No description provided for @checklistCompletedAt.
  ///
  /// In de, this message translates to:
  /// **'Abgeschlossen {timestamp}'**
  String checklistCompletedAt(String timestamp);

  /// No description provided for @loginAppBarTitle.
  ///
  /// In de, this message translates to:
  /// **'Anmelden'**
  String get loginAppBarTitle;

  /// No description provided for @loginChangeServer.
  ///
  /// In de, this message translates to:
  /// **'Server ändern'**
  String get loginChangeServer;

  /// No description provided for @loginHeading.
  ///
  /// In de, this message translates to:
  /// **'Anmeldung'**
  String get loginHeading;

  /// No description provided for @loginTokenLabel.
  ///
  /// In de, this message translates to:
  /// **'App-Token (wb_…)'**
  String get loginTokenLabel;

  /// No description provided for @loginTokenHelper.
  ///
  /// In de, this message translates to:
  /// **'Aus dem Web unter /konto/api/ – nötig bei MFA'**
  String get loginTokenHelper;

  /// No description provided for @loginTokenRequired.
  ///
  /// In de, this message translates to:
  /// **'Token erforderlich'**
  String get loginTokenRequired;

  /// No description provided for @loginUsername.
  ///
  /// In de, this message translates to:
  /// **'Benutzername'**
  String get loginUsername;

  /// No description provided for @loginUsernameRequired.
  ///
  /// In de, this message translates to:
  /// **'Benutzername erforderlich'**
  String get loginUsernameRequired;

  /// No description provided for @loginPassword.
  ///
  /// In de, this message translates to:
  /// **'Passwort'**
  String get loginPassword;

  /// No description provided for @loginPasswordRequired.
  ///
  /// In de, this message translates to:
  /// **'Passwort erforderlich'**
  String get loginPasswordRequired;

  /// No description provided for @loginShow.
  ///
  /// In de, this message translates to:
  /// **'Anzeigen'**
  String get loginShow;

  /// No description provided for @loginHide.
  ///
  /// In de, this message translates to:
  /// **'Verbergen'**
  String get loginHide;

  /// No description provided for @loginSubmit.
  ///
  /// In de, this message translates to:
  /// **'Anmelden'**
  String get loginSubmit;

  /// No description provided for @loginUseCredentials.
  ///
  /// In de, this message translates to:
  /// **'Mit Benutzername und Passwort'**
  String get loginUseCredentials;

  /// No description provided for @loginUseToken.
  ///
  /// In de, this message translates to:
  /// **'Stattdessen App-Token nutzen'**
  String get loginUseToken;

  /// No description provided for @loginTokenPasteHint.
  ///
  /// In de, this message translates to:
  /// **'Bitte App-Token einfügen (aus /konto/api/).'**
  String get loginTokenPasteHint;

  /// No description provided for @loginMfaHint.
  ///
  /// In de, this message translates to:
  /// **'Bei Zwei-Faktor: App-Token im Web unter Mein Konto → App-Tokens erzeugen.'**
  String get loginMfaHint;

  /// No description provided for @loginInvalidInput.
  ///
  /// In de, this message translates to:
  /// **'Ungültige Eingabe.'**
  String get loginInvalidInput;

  /// No description provided for @setupServerAddressTitle.
  ///
  /// In de, this message translates to:
  /// **'Server-Adresse Ihrer Wache'**
  String get setupServerAddressTitle;

  /// No description provided for @setupHint.
  ///
  /// In de, this message translates to:
  /// **'Geben Sie die Adresse ein oder scannen Sie den QR-Code aus dem Web.'**
  String get setupHint;

  /// No description provided for @setupAddressLabel.
  ///
  /// In de, this message translates to:
  /// **'Adresse'**
  String get setupAddressLabel;

  /// No description provided for @setupAddressHint.
  ///
  /// In de, this message translates to:
  /// **'https://wache.example.org'**
  String get setupAddressHint;

  /// No description provided for @setupScanQr.
  ///
  /// In de, this message translates to:
  /// **'QR-Code scannen'**
  String get setupScanQr;

  /// No description provided for @setupAddressRequired.
  ///
  /// In de, this message translates to:
  /// **'Adresse eingeben'**
  String get setupAddressRequired;

  /// No description provided for @setupAddressInvalid.
  ///
  /// In de, this message translates to:
  /// **'Ungültige Adresse'**
  String get setupAddressInvalid;

  /// No description provided for @setupConfirm.
  ///
  /// In de, this message translates to:
  /// **'Bestätigen'**
  String get setupConfirm;

  /// No description provided for @setupFooter.
  ///
  /// In de, this message translates to:
  /// **'Play-Store-Client: Verbindung nur zu Ihrem selbst gehosteten Server. Produktion: HTTPS erforderlich.'**
  String get setupFooter;

  /// No description provided for @qrScanTitle.
  ///
  /// In de, this message translates to:
  /// **'Server-QR scannen'**
  String get qrScanTitle;

  /// No description provided for @qrScanCameraHint.
  ///
  /// In de, this message translates to:
  /// **'Die Kamera wird nur zum Lesen der Server-Adresse genutzt. Es werden keine Fotos gespeichert oder hochgeladen.'**
  String get qrScanCameraHint;

  /// No description provided for @qrScanInvalid.
  ///
  /// In de, this message translates to:
  /// **'Kein gültiger Wachbuch-Server-QR.'**
  String get qrScanInvalid;

  /// No description provided for @qrScanWebHint.
  ///
  /// In de, this message translates to:
  /// **'QR aus dem Wachbuch-Web unter Mein Konto → App-Tokens'**
  String get qrScanWebHint;

  /// No description provided for @qrCameraDialogTitle.
  ///
  /// In de, this message translates to:
  /// **'Kamera für QR-Code'**
  String get qrCameraDialogTitle;

  /// No description provided for @qrCameraDialogMessage.
  ///
  /// In de, this message translates to:
  /// **'Wachbuch benötigt die Kamera ausschließlich, um den QR-Code mit der Server-Adresse Ihrer Wache zu scannen. Ohne Kamera können Sie die Adresse auch manuell eingeben.'**
  String get qrCameraDialogMessage;

  /// No description provided for @qrCameraContinue.
  ///
  /// In de, this message translates to:
  /// **'Weiter'**
  String get qrCameraContinue;

  /// No description provided for @qrCameraDeniedTitle.
  ///
  /// In de, this message translates to:
  /// **'Kamera nicht freigegeben'**
  String get qrCameraDeniedTitle;

  /// No description provided for @qrCameraDeniedMessage.
  ///
  /// In de, this message translates to:
  /// **'Ohne Kamerazugriff können Sie den QR nicht scannen. Geben Sie die Server-Adresse manuell ein oder aktivieren Sie die Kamera in den Systemeinstellungen.'**
  String get qrCameraDeniedMessage;

  /// No description provided for @qrCameraOk.
  ///
  /// In de, this message translates to:
  /// **'OK'**
  String get qrCameraOk;

  /// No description provided for @qrCameraSettings.
  ///
  /// In de, this message translates to:
  /// **'Einstellungen'**
  String get qrCameraSettings;

  /// No description provided for @handoverStatusOpen.
  ///
  /// In de, this message translates to:
  /// **'Offen'**
  String get handoverStatusOpen;

  /// No description provided for @handoverStatusInProgress.
  ///
  /// In de, this message translates to:
  /// **'In Bearbeitung'**
  String get handoverStatusInProgress;

  /// No description provided for @handoverStatusDone.
  ///
  /// In de, this message translates to:
  /// **'Erledigt'**
  String get handoverStatusDone;

  /// No description provided for @handoverPriorityNormal.
  ///
  /// In de, this message translates to:
  /// **'Normal'**
  String get handoverPriorityNormal;

  /// No description provided for @handoverPriorityImportant.
  ///
  /// In de, this message translates to:
  /// **'Wichtig'**
  String get handoverPriorityImportant;

  /// No description provided for @handoverPriorityUrgent.
  ///
  /// In de, this message translates to:
  /// **'Dringend'**
  String get handoverPriorityUrgent;

  /// No description provided for @handoverCategoryStation.
  ///
  /// In de, this message translates to:
  /// **'Wache'**
  String get handoverCategoryStation;

  /// No description provided for @handoverCategoryVehicle.
  ///
  /// In de, this message translates to:
  /// **'Fahrzeugstatus'**
  String get handoverCategoryVehicle;

  /// No description provided for @handoverCategoryMaterial.
  ///
  /// In de, this message translates to:
  /// **'Material'**
  String get handoverCategoryMaterial;

  /// No description provided for @handoverCategoryTask.
  ///
  /// In de, this message translates to:
  /// **'Offene Aufgabe'**
  String get handoverCategoryTask;

  /// No description provided for @handoverCategorySafety.
  ///
  /// In de, this message translates to:
  /// **'Sicherheit/Mangel'**
  String get handoverCategorySafety;

  /// No description provided for @handoverEnumUnknown.
  ///
  /// In de, this message translates to:
  /// **'Nicht angegeben'**
  String get handoverEnumUnknown;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['de', 'en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'de':
      return AppLocalizationsDe();
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
