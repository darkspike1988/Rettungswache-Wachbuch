import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:wachbuch_mobile/l10n/generated/app_localizations.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/api/server_address.dart';
import 'package:wachbuch_mobile/api/server_links.dart';
import 'package:wachbuch_mobile/auth/session_store.dart';
import 'package:wachbuch_mobile/screens/home_shell.dart';
import 'package:wachbuch_mobile/screens/login_screen.dart';
import 'package:wachbuch_mobile/screens/server_setup_screen.dart';
import 'package:wachbuch_mobile/theme/app_theme.dart';
import 'package:wachbuch_mobile/theme/solar_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final store = SessionStore();
  final links = AppLinksServerLinkSource();
  final themeController = SolarThemeController.device();
  runApp(
    WachbuchApp(
      store: store,
      linkSource: links,
      themeController: themeController,
    ),
  );
}

enum _BootPhase { booting, setupServer, login, home }

class WachbuchApp extends StatefulWidget {
  const WachbuchApp({
    super.key,
    required this.store,
    this.linkSource = const NoopServerLinkSource(),
    this.themeController,
  });

  final SessionStore store;
  final ServerLinkSource linkSource;
  final SolarThemeController? themeController;

  @override
  State<WachbuchApp> createState() => _WachbuchAppState();
}

class _WachbuchAppState extends State<WachbuchApp> with WidgetsBindingObserver {
  final _navigatorKey = GlobalKey<NavigatorState>();
  _BootPhase _phase = _BootPhase.booting;
  String? _serverUrl;
  WachbuchApi? _api;
  StreamSubscription<Uri>? _linkSubscription;
  ThemeMode _themeMode = ThemeMode.system;
  String? _sessionNotice;

  @override
  void initState() {
    super.initState();
    final themeController = widget.themeController;
    if (themeController != null) {
      _themeMode = themeController.mode;
      themeController.addListener(_handleThemeChange);
      WidgetsBinding.instance.addObserver(this);
      unawaited(themeController.refresh());
    }
    _bootstrap();
  }

  void _handleThemeChange() {
    if (!mounted) return;
    setState(() {
      _themeMode = widget.themeController?.mode ?? ThemeMode.system;
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      final controller = widget.themeController;
      if (controller != null) unawaited(controller.refresh());
    }
  }

  Future<void> _bootstrap() async {
    var url = await widget.store.readServerUrl();
    var token = await widget.store.readToken();

    if (url != null && url.isNotEmpty) {
      try {
        url = parseServerAddress(url, allowInsecure: kDebugMode);
        await widget.store.writeServerUrl(url);
      } on ArgumentError {
        await widget.store.clearAll();
        url = null;
        token = null;
      }
    }

    if (token != null && await widget.store.isTokenExpired()) {
      await widget.store.clearToken();
      token = null;
      _sessionNotice = 'Ihre Anmeldung ist abgelaufen. Bitte erneut anmelden.';
    }

    final initialLink = await widget.linkSource.getInitialLink();
    if (initialLink != null) {
      final linkedUrl = _parseLink(initialLink);
      // Cold-start via deep link is intentional; confirm only for hot links.
      if (linkedUrl != null &&
          await _applyServerLink(linkedUrl, confirmIfNeeded: false)) {
        url = linkedUrl;
        token = null;
      }
    }

    if (!mounted) return;
    setState(() {
      _serverUrl = url;
      if (url != null && url.isNotEmpty && token != null && token.isNotEmpty) {
        _api = WachbuchApi(baseUrl: url, token: token);
        _phase = _BootPhase.home;
      } else if (url != null && url.isNotEmpty) {
        _phase = _BootPhase.login;
      } else {
        _phase = _BootPhase.setupServer;
      }
    });

    _linkSubscription = widget.linkSource.uriLinkStream.listen(
      _handleServerLink,
      onError: (_) {},
    );
  }

  String? _parseLink(Uri link) {
    try {
      return parseServerAddress(link.toString(), allowInsecure: kDebugMode);
    } on ArgumentError {
      return null;
    }
  }

  Future<bool> _applyServerLink(
    String url, {
    required bool confirmIfNeeded,
  }) async {
    if (confirmIfNeeded) {
      final nav = _navigatorKey.currentContext;
      if (nav == null) return false;
      final confirmed = await showDialog<bool>(
        context: nav,
        builder: (context) => AlertDialog(
          title: const Text('Server wechseln?'),
          content: Text(
            'Ein Link möchte die App auf\n$url\numstellen. '
            'Die aktuelle Anmeldung wird dabei beendet.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Wechseln'),
            ),
          ],
        ),
      );
      if (confirmed != true) return false;
    }
    await widget.store.clearAll();
    await widget.store.writeServerUrl(url);
    return true;
  }

  Future<void> _handleServerLink(Uri link) async {
    final url = _parseLink(link);
    if (url == null) return;
    if (_serverUrl == url && _phase == _BootPhase.home) {
      return;
    }
    final needsConfirm =
        _phase == _BootPhase.home &&
        _serverUrl != null &&
        _serverUrl != url;
    final applied = await _applyServerLink(
      url,
      confirmIfNeeded: needsConfirm,
    );
    if (!applied || !mounted) return;
    setState(() {
      _api = null;
      _serverUrl = url;
      _phase = _BootPhase.login;
      _sessionNotice = null;
    });
  }

  @override
  void dispose() {
    _linkSubscription?.cancel();
    final themeController = widget.themeController;
    if (themeController != null) {
      WidgetsBinding.instance.removeObserver(this);
      themeController.removeListener(_handleThemeChange);
      themeController.dispose();
    }
    super.dispose();
  }

  Future<void> _onServerReady(String url) async {
    await widget.store.writeServerUrl(url);
    if (!mounted) return;
    setState(() {
      _serverUrl = url;
      _phase = _BootPhase.login;
    });
  }

  Future<void> _onLoggedIn(
    String url,
    String token, {
    DateTime? expiresAt,
  }) async {
    await widget.store.writeServerUrl(url);
    await widget.store.writeToken(token, expiresAt: expiresAt);
    if (!mounted) return;
    setState(() {
      _serverUrl = url;
      _api = WachbuchApi(baseUrl: url, token: token);
      _phase = _BootPhase.home;
      _sessionNotice = null;
    });
  }

  Future<void> _logout({String? notice}) async {
    await widget.store.clearToken();
    if (!mounted) return;
    setState(() {
      _api = null;
      _sessionNotice = notice;
      _phase = _serverUrl == null || _serverUrl!.isEmpty
          ? _BootPhase.setupServer
          : _BootPhase.login;
    });
  }

  Future<void> _changeServer() async {
    await widget.store.clearAll();
    if (!mounted) return;
    setState(() {
      _api = null;
      _serverUrl = null;
      _sessionNotice = null;
      _phase = _BootPhase.setupServer;
    });
  }

  @override
  Widget build(BuildContext context) {
    Widget home;
    switch (_phase) {
      case _BootPhase.booting:
        home = const Scaffold(body: Center(child: CircularProgressIndicator()));
      case _BootPhase.setupServer:
        home = ServerSetupScreen(
          store: widget.store,
          onServerReady: _onServerReady,
        );
      case _BootPhase.login:
        home = LoginScreen(
          store: widget.store,
          serverUrl: _serverUrl!,
          notice: _sessionNotice,
          onLoggedIn: _onLoggedIn,
          onChangeServer: _changeServer,
        );
      case _BootPhase.home:
        home = HomeShell(
          api: _api!,
          onLogout: () => _logout(
            notice: 'Sitzung beendet. Bitte erneut anmelden.',
          ),
          onChangeServer: _changeServer,
        );
    }

    return MaterialApp(
      title: 'Wachbuch',
      navigatorKey: _navigatorKey,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      theme: buildWachbuchTheme(Brightness.light),
      darkTheme: buildWachbuchTheme(Brightness.dark),
      themeMode: _themeMode,
      home: home,
    );
  }
}
