import 'package:flutter/material.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/auth/session_store.dart';
import 'package:wachbuch_mobile/screens/home_shell.dart';
import 'package:wachbuch_mobile/screens/login_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final store = SessionStore();
  runApp(WachbuchApp(store: store));
}

class WachbuchApp extends StatefulWidget {
  const WachbuchApp({super.key, required this.store});

  final SessionStore store;

  @override
  State<WachbuchApp> createState() => _WachbuchAppState();
}

class _WachbuchAppState extends State<WachbuchApp> {
  bool _booting = true;
  WachbuchApi? _api;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    final url = await widget.store.readServerUrl();
    final token = await widget.store.readToken();
    if (url != null && token != null && token.isNotEmpty) {
      setState(() {
        _api = WachbuchApi(baseUrl: url, token: token);
        _booting = false;
      });
      return;
    }
    setState(() => _booting = false);
  }

  Future<void> _onLoggedIn(String url, String token) async {
    await widget.store.writeServerUrl(url);
    await widget.store.writeToken(token);
    setState(() => _api = WachbuchApi(baseUrl: url, token: token));
  }

  Future<void> _logout() async {
    await widget.store.clearToken();
    setState(() => _api = null);
  }

  @override
  Widget build(BuildContext context) {
    final seed = const Color(0xFF1F4D3A);
    return MaterialApp(
      title: 'Wachbuch',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: seed, brightness: Brightness.light),
        useMaterial3: true,
      ),
      home: _booting
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : _api == null
              ? LoginScreen(store: widget.store, onLoggedIn: _onLoggedIn)
              : HomeShell(api: _api!, onLogout: _logout),
    );
  }
}
