import 'package:flutter/material.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/auth/session_store.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.store,
    required this.onLoggedIn,
  });

  final SessionStore store;
  final Future<void> Function(String serverUrl, String token) onLoggedIn;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _serverCtrl = TextEditingController();
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _tokenCtrl = TextEditingController();
  bool _busy = false;
  bool _useTokenPaste = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.store.readServerUrl().then((url) {
      if (url != null && mounted) {
        _serverCtrl.text = url;
      }
    });
  }

  @override
  void dispose() {
    _serverCtrl.dispose();
    _userCtrl.dispose();
    _passCtrl.dispose();
    _tokenCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final url = normalizeServerUrl(_serverCtrl.text);
      final api = WachbuchApi(baseUrl: url);
      await api.discover();
      late final String token;
      if (_useTokenPaste) {
        token = _tokenCtrl.text.trim();
        if (token.isEmpty) {
          throw ApiException(400, 'Bitte App-Token einfügen (aus /konto/api/).');
        }
        // Validate token against /me/
        await api.copyWithToken(token).me();
      } else {
        token = await api.obtainToken(
          username: _userCtrl.text.trim(),
          password: _passCtrl.text,
          label: 'Wachbuch Mobile',
        );
      }
      await widget.onLoggedIn(url, token);
    } on ApiException catch (error) {
      setState(() {
        _error = error.message;
        if (error.statusCode == 403 && error.message.contains('MFA')) {
          _error =
              '${error.message}\n\nTipp: Im Browser unter Mein Konto → App-Tokens ein Token erzeugen und hier einfügen.';
          _useTokenPaste = true;
        }
      });
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 24),
            Text(
              'Wachbuch',
              style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Selbst gehostet · eine Wache · AGPL',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 32),
            TextField(
              controller: _serverCtrl,
              decoration: const InputDecoration(
                labelText: 'Server-URL',
                hintText: 'https://wache.example.org',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.url,
              autocorrect: false,
            ),
            const SizedBox(height: 16),
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text('Login')),
                ButtonSegment(value: true, label: Text('App-Token')),
              ],
              selected: {_useTokenPaste},
              onSelectionChanged: (value) {
                setState(() => _useTokenPaste = value.first);
              },
            ),
            const SizedBox(height: 16),
            if (_useTokenPaste)
              TextField(
                controller: _tokenCtrl,
                decoration: const InputDecoration(
                  labelText: 'App-Token (wb_…)',
                  border: OutlineInputBorder(),
                  helperText: 'Aus dem Web unter /konto/api/ – nötig bei MFA',
                ),
                obscureText: true,
              )
            else ...[
              TextField(
                controller: _userCtrl,
                decoration: const InputDecoration(
                  labelText: 'Benutzername',
                  border: OutlineInputBorder(),
                ),
                autocorrect: false,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _passCtrl,
                decoration: const InputDecoration(
                  labelText: 'Passwort',
                  border: OutlineInputBorder(),
                ),
                obscureText: true,
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: _busy
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Mit Wache verbinden'),
            ),
            const SizedBox(height: 16),
            Text(
              'Wie Nextcloud/Paperless: Die App speichert nur die Server-URL und ein widerrufbares Token. Die Wache kommt aus der Mitgliedschaft auf dem Server.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
