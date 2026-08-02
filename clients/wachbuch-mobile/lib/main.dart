import 'package:flutter/material.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/auth/session_store.dart';
import 'package:wachbuch_mobile/screens/home_shell.dart';
import 'package:wachbuch_mobile/screens/login_screen.dart';
import 'package:wachbuch_mobile/screens/server_setup_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final store = SessionStore();
  runApp(WachbuchApp(store: store));
}

enum _BootPhase { booting, setupServer, login, home }

class WachbuchApp extends StatefulWidget {
  const WachbuchApp({super.key, required this.store});

  final SessionStore store;

  @override
  State<WachbuchApp> createState() => _WachbuchAppState();
}

class _WachbuchAppState extends State<WachbuchApp> {
  _BootPhase _phase = _BootPhase.booting;
  String? _serverUrl;
  WachbuchApi? _api;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    final url = await widget.store.readServerUrl();
    final token = await widget.store.readToken();
    if (!mounted) return;
    if (url != null && url.isNotEmpty && token != null && token.isNotEmpty) {
      setState(() {
        _serverUrl = url;
        _api = WachbuchApi(baseUrl: url, token: token);
        _phase = _BootPhase.home;
      });
      return;
    }
    if (url != null && url.isNotEmpty) {
      setState(() {
        _serverUrl = url;
        _phase = _BootPhase.login;
      });
      return;
    }
    setState(() => _phase = _BootPhase.setupServer);
  }

  Future<void> _onServerReady(String url) async {
    await widget.store.writeServerUrl(url);
    if (!mounted) return;
    setState(() {
      _serverUrl = url;
      _phase = _BootPhase.login;
    });
  }

  Future<void> _onLoggedIn(String url, String token) async {
    await widget.store.writeServerUrl(url);
    await widget.store.writeToken(token);
    if (!mounted) return;
    setState(() {
      _serverUrl = url;
      _api = WachbuchApi(baseUrl: url, token: token);
      _phase = _BootPhase.home;
    });
  }

  Future<void> _logout() async {
    await widget.store.clearToken();
    if (!mounted) return;
    setState(() {
      _api = null;
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
      _phase = _BootPhase.setupServer;
    });
  }

  ThemeData _theme(Brightness brightness) {
    const seed = Color(0xFF1F4D3A);
    final scheme = ColorScheme.fromSeed(seedColor: seed, brightness: brightness);
    return ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      inputDecorationTheme: const InputDecorationTheme(
        filled: false,
        border: OutlineInputBorder(),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(48),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        height: 72,
        indicatorColor: scheme.secondaryContainer,
      ),
    );
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
          onLoggedIn: _onLoggedIn,
          onChangeServer: _changeServer,
        );
      case _BootPhase.home:
        home = HomeShell(
          api: _api!,
          onLogout: _logout,
          onChangeServer: _changeServer,
        );
    }

    return MaterialApp(
      title: 'Wachbuch',
      theme: _theme(Brightness.light),
      darkTheme: _theme(Brightness.dark),
      themeMode: ThemeMode.system,
      home: home,
    );
  }
}
