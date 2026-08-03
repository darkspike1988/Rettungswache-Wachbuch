import 'package:flutter/material.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/api/server_address.dart';
import 'package:wachbuch_mobile/auth/session_store.dart';
import 'package:wachbuch_mobile/screens/qr_scan_screen.dart';
import 'package:wachbuch_mobile/ui/error_banner.dart';
import 'package:wachbuch_mobile/ui/layout.dart';

/// First screen: only server address (typed or QR) + confirm.
/// Matches Nextcloud/Paperless self-host onboarding and Material 3 forms.
class ServerSetupScreen extends StatefulWidget {
  const ServerSetupScreen({
    super.key,
    required this.store,
    required this.onServerReady,
    this.apiFactory = defaultWachbuchApiFactory,
  });

  final SessionStore store;
  final Future<void> Function(String serverUrl) onServerReady;
  final WachbuchApiFactory apiFactory;

  @override
  State<ServerSetupScreen> createState() => _ServerSetupScreenState();
}

class _ServerSetupScreenState extends State<ServerSetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _addressCtrl = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _addressCtrl.dispose();
    super.dispose();
  }

  Future<void> _scanQr() async {
    final address = await openServerQrScanner(context);
    if (address != null && mounted) {
      setState(() {
        _addressCtrl.text = address;
        _error = null;
      });
    }
  }

  Future<void> _confirm() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    WachbuchApi? api;
    try {
      final url = parseServerAddress(_addressCtrl.text);
      api = widget.apiFactory(url);
      await api.discover();
      await widget.onServerReady(url);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
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
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: maxW),
            child: Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(24),
                children: [
                  const SizedBox(height: 32),
                  Icon(
                    Icons.apartment_outlined,
                    size: AppLayout.isTablet(width) ? 64 : 52,
                    color: scheme.primary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Wachbuch',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Server-Adresse Ihrer Wache',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Geben Sie die Adresse ein oder scannen Sie den QR-Code aus dem Web.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 32),
                  TextFormField(
                    controller: _addressCtrl,
                    decoration: InputDecoration(
                      labelText: 'Adresse',
                      hintText: 'https://wache.example.org',
                      border: const OutlineInputBorder(),
                      prefixIcon: const Icon(Icons.link),
                      suffixIcon: IconButton(
                        tooltip: 'QR-Code scannen',
                        onPressed: _busy ? null : _scanQr,
                        icon: const Icon(Icons.qr_code_scanner),
                      ),
                    ),
                    keyboardType: TextInputType.url,
                    textInputAction: TextInputAction.done,
                    autocorrect: false,
                    enableSuggestions: false,
                    autofillHints: const [AutofillHints.url],
                    onFieldSubmitted: (_) {
                      if (!_busy) _confirm();
                    },
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Adresse eingeben';
                      }
                      try {
                        parseServerAddress(value);
                      } catch (_) {
                        return 'Ungültige Adresse';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _scanQr,
                    icon: const Icon(Icons.photo_camera_outlined),
                    label: const Text('QR-Code scannen'),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 16),
                    ErrorBanner(message: _error!),
                  ],
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _busy ? null : _confirm,
                    child: _busy
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Bestätigen'),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Play-Store-Client: Verbindung nur zu Ihrem selbst gehosteten Server. '
                    'Produktion: HTTPS erforderlich.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
