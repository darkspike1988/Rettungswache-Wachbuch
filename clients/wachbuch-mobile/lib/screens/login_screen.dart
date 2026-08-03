import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/auth/session_store.dart';
import 'package:wachbuch_mobile/ui/error_banner.dart';
import 'package:wachbuch_mobile/ui/layout.dart';

/// Second screen: username + password against the chosen server.
class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.store,
    required this.serverUrl,
    required this.onLoggedIn,
    required this.onChangeServer,
    this.notice,
    this.apiFactory = defaultWachbuchApiFactory,
  });

  final SessionStore store;
  final String serverUrl;
  final String? notice;
  final Future<void> Function(
    String serverUrl,
    String token, {
    DateTime? expiresAt,
  })
  onLoggedIn;
  final Future<void> Function() onChangeServer;
  final WachbuchApiFactory apiFactory;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _tokenCtrl = TextEditingController();
  bool _busy = false;
  bool _useTokenPaste = false;
  bool _obscure = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _error = widget.notice;
  }

  @override
  void didUpdateWidget(covariant LoginScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.notice != oldWidget.notice && widget.notice != null) {
      _error = widget.notice;
    }
  }

  @override
  void dispose() {
    _userCtrl.dispose();
    _passCtrl.dispose();
    _tokenCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    WachbuchApi? api;
    try {
      api = widget.apiFactory(widget.serverUrl);
      late final String token;
      DateTime? expiresAt;
      if (_useTokenPaste) {
        token = _tokenCtrl.text.trim();
        if (token.isEmpty) {
          throw ApiException(
            400,
            'Bitte App-Token einfügen (aus /konto/api/).',
          );
        }
        await api.copyWithToken(token).me();
      } else {
        final auth = await api.obtainToken(
          username: _userCtrl.text.trim(),
          password: _passCtrl.text,
          label: 'Wachbuch Mobile',
        );
        token = auth.value;
        expiresAt = auth.expiresAt;
      }
      TextInput.finishAutofillContext(shouldSave: true);
      _passCtrl.clear();
      _tokenCtrl.clear();
      await widget.onLoggedIn(
        widget.serverUrl,
        token,
        expiresAt: expiresAt,
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        if (error.isMfaRequired) {
          _error =
              '${error.message}\n\nBei Zwei-Faktor: App-Token im Web unter Mein Konto → App-Tokens erzeugen.';
          _useTokenPaste = true;
        }
      });
    } catch (error) {
      if (!mounted) return;
      final message = error is ArgumentError
          ? (error.message?.toString() ?? 'Ungültige Eingabe.')
          : error.toString();
      setState(() => _error = message);
    } finally {
      api?.close();
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final maxW = AppLayout.isTablet(width) ? 480.0 : 420.0;
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Anmelden'),
        leading: IconButton(
          tooltip: 'Server ändern',
          onPressed: _busy ? null : () => widget.onChangeServer(),
          icon: const Icon(Icons.arrow_back),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: maxW),
            child: AutofillGroup(
              child: Form(
                key: _formKey,
                child: ListView(
                  padding: const EdgeInsets.all(24),
                  children: [
                    Text(
                      'Anmeldung',
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      widget.serverUrl,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 28),
                    if (_useTokenPaste)
                      TextFormField(
                        controller: _tokenCtrl,
                        decoration: const InputDecoration(
                          labelText: 'App-Token (wb_…)',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.key_outlined),
                          helperText:
                              'Aus dem Web unter /konto/api/ – nötig bei MFA',
                        ),
                        obscureText: true,
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Token erforderlich'
                            : null,
                      )
                    else ...[
                      TextFormField(
                        controller: _userCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Benutzername',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.person_outline),
                        ),
                        textInputAction: TextInputAction.next,
                        autocorrect: false,
                        enableSuggestions: false,
                        autofillHints: const [AutofillHints.username],
                        inputFormatters: [
                          FilteringTextInputFormatter.deny(RegExp(r'\s')),
                        ],
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Benutzername erforderlich'
                            : null,
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _passCtrl,
                        decoration: InputDecoration(
                          labelText: 'Passwort',
                          border: const OutlineInputBorder(),
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            tooltip: _obscure ? 'Anzeigen' : 'Verbergen',
                            onPressed: () =>
                                setState(() => _obscure = !_obscure),
                            icon: Icon(
                              _obscure
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                            ),
                          ),
                        ),
                        obscureText: _obscure,
                        textInputAction: TextInputAction.done,
                        autofillHints: const [AutofillHints.password],
                        onFieldSubmitted: (_) {
                          if (!_busy) _submit();
                        },
                        validator: (v) => (v == null || v.isEmpty)
                            ? 'Passwort erforderlich'
                            : null,
                      ),
                    ],
                    if (_error != null) ...[
                      const SizedBox(height: 16),
                      ErrorBanner(message: _error!),
                    ],
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _busy ? null : _submit,
                      child: _busy
                          ? const SizedBox(
                              height: 22,
                              width: 22,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Anmelden'),
                    ),
                    const SizedBox(height: 12),
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () => setState(() {
                              _useTokenPaste = !_useTokenPaste;
                              _error = null;
                            }),
                      child: Text(
                        _useTokenPaste
                            ? 'Mit Benutzername und Passwort'
                            : 'Stattdessen App-Token nutzen',
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
