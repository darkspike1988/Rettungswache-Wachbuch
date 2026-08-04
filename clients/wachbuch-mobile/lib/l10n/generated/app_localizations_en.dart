// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'Wachbuch';

  @override
  String errorSemanticsLabel(String message) {
    return 'Error: $message';
  }

  @override
  String get commonCancel => 'Cancel';

  @override
  String get commonSwitch => 'Switch';

  @override
  String get noticeSessionExpired =>
      'Your session has expired. Please sign in again.';

  @override
  String get noticeSessionEnded => 'Session ended. Please sign in again.';

  @override
  String get serverSwitchTitle => 'Switch server?';

  @override
  String serverSwitchMessage(String url) {
    return 'A link wants to switch the app to\n$url.\nThe current login will be ended.';
  }

  @override
  String get navOverview => 'Overview';

  @override
  String get navHandovers => 'Handovers';

  @override
  String get navAccount => 'Account';

  @override
  String get refreshTooltip => 'Refresh';

  @override
  String get stationFallback => 'Wachbuch';

  @override
  String get sessionExpiredError => 'Login expired or revoked.';

  @override
  String get overviewActiveHandovers => 'Active handovers';

  @override
  String get metricOpen => 'open';

  @override
  String get metricInProgress => 'in progress';

  @override
  String get metricUrgent => 'urgent';

  @override
  String get overviewModulesTitle => 'Modules of this station';

  @override
  String get overviewModulesHint =>
      'Your station and the available modules are loaded automatically from your account.';

  @override
  String get moduleCalendarTitle => 'Calendar';

  @override
  String get moduleCalendarSubtitle => 'Shift schedules and duties';

  @override
  String get moduleCoffeeTitle => 'Coffee fund';

  @override
  String get moduleCoffeeSubtitle => 'Balance and transactions';

  @override
  String get moduleChecklistsTitle => 'Checklists';

  @override
  String get moduleChecklistsSubtitle => 'Tick off items and complete';

  @override
  String get quickAccessTitle => 'Quick access';

  @override
  String get handoverSearchHint => 'Search handovers';

  @override
  String get handoverSearchClear => 'Clear search';

  @override
  String get filterStatus => 'Status';

  @override
  String get filterPriority => 'Priority';

  @override
  String handoversCount(int count, int total) {
    return '$count of $total handovers';
  }

  @override
  String filterSectionLabel(String title) {
    return 'Filter $title';
  }

  @override
  String get handoversNoneActive => 'No active handovers.';

  @override
  String get handoversNoneForFilter => 'No handovers match these filters.';

  @override
  String get handoverUntitled => 'untitled';

  @override
  String get handoverFallback => 'Handover';

  @override
  String handoverOpenSemantics(String title) {
    return 'Open handover $title';
  }

  @override
  String get detailsLoadFailed => 'Details could not be loaded.';

  @override
  String get detailsNoFurtherInfo => 'No further details.';

  @override
  String detailsUpdatedAt(String timestamp) {
    return 'Updated $timestamp';
  }

  @override
  String detailsVersion(String version) {
    return 'Version $version';
  }

  @override
  String get accountLoggedInAs => 'Signed in as';

  @override
  String get accountServer => 'Server';

  @override
  String get accountLicense => 'License';

  @override
  String get accountLicenseValue => 'AGPL-3.0-or-later · Open source';

  @override
  String get accountRefreshProfile => 'Refresh profile';

  @override
  String get accountLogout => 'Sign out';

  @override
  String get accountChangeServer => 'Set up another server';

  @override
  String get kalenderTitle => 'Calendar';

  @override
  String get kalenderEmpty => 'No upcoming appointments.';

  @override
  String get kalenderEntryFallback => 'Appointment';

  @override
  String get kalenderTimeTbd => 'Time to be announced';

  @override
  String get kalenderAllDay => 'All day';

  @override
  String get kaffeekasseTitle => 'Coffee fund';

  @override
  String get kaffeekasseBalanceLabel => 'Current balance';

  @override
  String get kaffeekasseNegative =>
      'The fund is in the negative – please top up.';

  @override
  String get kaffeekasseLastTransactions => 'Recent transactions';

  @override
  String get kaffeekasseEmptyLedger => 'No transactions yet.';

  @override
  String get kaffeekasseEntryFallback => 'Transaction';

  @override
  String get checklistenTitle => 'Checklists';

  @override
  String get checklistenEmpty => 'No checklists available.';

  @override
  String get checklistFallback => 'Checklist';

  @override
  String get checklistNoItems => 'No items.';

  @override
  String get checklistCompleteButton => 'Complete checklist';

  @override
  String get checklistItemFallback => 'Item';

  @override
  String checklistCompletedAt(String timestamp) {
    return 'Completed $timestamp';
  }

  @override
  String get loginAppBarTitle => 'Sign in';

  @override
  String get loginChangeServer => 'Change server';

  @override
  String get loginHeading => 'Sign in';

  @override
  String get loginTokenLabel => 'App token (wb_…)';

  @override
  String get loginTokenHelper =>
      'From the web at /konto/api/ – required for MFA';

  @override
  String get loginTokenRequired => 'Token required';

  @override
  String get loginUsername => 'Username';

  @override
  String get loginUsernameRequired => 'Username required';

  @override
  String get loginPassword => 'Password';

  @override
  String get loginPasswordRequired => 'Password required';

  @override
  String get loginShow => 'Show';

  @override
  String get loginHide => 'Hide';

  @override
  String get loginSubmit => 'Sign in';

  @override
  String get loginUseCredentials => 'With username and password';

  @override
  String get loginUseToken => 'Use an app token instead';

  @override
  String get loginTokenPasteHint =>
      'Please paste an app token (from /konto/api/).';

  @override
  String get loginMfaHint =>
      'For two-factor: create an app token on the web under My Account → App Tokens.';

  @override
  String get loginInvalidInput => 'Invalid input.';

  @override
  String get setupServerAddressTitle => 'Server address of your station';

  @override
  String get setupHint => 'Enter the address or scan the QR code from the web.';

  @override
  String get setupAddressLabel => 'Address';

  @override
  String get setupAddressHint => 'https://station.example.org';

  @override
  String get setupScanQr => 'Scan QR code';

  @override
  String get setupAddressRequired => 'Enter an address';

  @override
  String get setupAddressInvalid => 'Invalid address';

  @override
  String get setupConfirm => 'Confirm';

  @override
  String get setupFooter =>
      'Play Store client: connects only to your self-hosted server. Production: HTTPS required.';

  @override
  String get qrScanTitle => 'Scan server QR';

  @override
  String get qrScanCameraHint =>
      'The camera is used only to read the server address. No photos are saved or uploaded.';

  @override
  String get qrScanInvalid => 'Not a valid Wachbuch server QR code.';

  @override
  String get qrScanWebHint =>
      'QR from the Wachbuch web under My Account → App Tokens';

  @override
  String get qrCameraDialogTitle => 'Camera for QR code';

  @override
  String get qrCameraDialogMessage =>
      'Wachbuch needs the camera solely to scan the QR code containing your station\'s server address. You can also enter the address manually without the camera.';

  @override
  String get qrCameraContinue => 'Continue';

  @override
  String get qrCameraDeniedTitle => 'Camera not enabled';

  @override
  String get qrCameraDeniedMessage =>
      'Without camera access you cannot scan the QR code. Enter the server address manually or enable the camera in the system settings.';

  @override
  String get qrCameraOk => 'OK';

  @override
  String get qrCameraSettings => 'Settings';

  @override
  String get handoverStatusOpen => 'Open';

  @override
  String get handoverStatusInProgress => 'In progress';

  @override
  String get handoverStatusDone => 'Done';

  @override
  String get handoverPriorityNormal => 'Normal';

  @override
  String get handoverPriorityImportant => 'Important';

  @override
  String get handoverPriorityUrgent => 'Urgent';

  @override
  String get handoverCategoryStation => 'Station';

  @override
  String get handoverCategoryVehicle => 'Vehicle status';

  @override
  String get handoverCategoryMaterial => 'Material';

  @override
  String get handoverCategoryTask => 'Open task';

  @override
  String get handoverCategorySafety => 'Safety/defect';

  @override
  String get handoverEnumUnknown => 'Not specified';
}
