import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:wachbuch_mobile/api/server_address.dart';

/// Full-screen QR scanner for the Wachbuch server address.
///
/// Camera is only used for this setup step (Play User Data / Camera policy:
/// permission requested just-in-time with an on-screen purpose explanation).
class QrScanScreen extends StatefulWidget {
  const QrScanScreen({super.key});

  @override
  State<QrScanScreen> createState() => _QrScanScreenState();
}

class _QrScanScreenState extends State<QrScanScreen> {
  final MobileScannerController _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.normal,
    facing: CameraFacing.back,
    formats: const [BarcodeFormat.qrCode],
  );
  bool _handled = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_handled) return;
    for (final barcode in capture.barcodes) {
      final raw = barcode.rawValue;
      if (raw == null || raw.trim().isEmpty) continue;
      try {
        final address = parseServerAddress(raw);
        _handled = true;
        await _controller.stop();
        if (!mounted) return;
        Navigator.of(context).pop(address);
        return;
      } catch (_) {
        setState(() => _error = 'Kein gültiger Wachbuch-Server-QR.');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Server-QR scannen'),
      ),
      body: Column(
        children: [
          Material(
            color: scheme.secondaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'Die Kamera wird nur zum Lesen der Server-Adresse genutzt. '
                'Es werden keine Fotos gespeichert oder hochgeladen.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: scheme.onSecondaryContainer,
                    ),
              ),
            ),
          ),
          Expanded(
            child: Stack(
              fit: StackFit.expand,
              children: [
                MobileScanner(
                  controller: _controller,
                  onDetect: _onDetect,
                ),
                Align(
                  alignment: Alignment.center,
                  child: Container(
                    width: 240,
                    height: 240,
                    decoration: BoxDecoration(
                      border: Border.all(color: scheme.primary, width: 3),
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(12),
              child: Text(_error!, style: TextStyle(color: scheme.error)),
            ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'QR aus dem Wachbuch-Web unter Mein Konto → App-Tokens',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Explains camera use (Play policy) then requests permission and opens scanner.
Future<String?> openServerQrScanner(BuildContext context) async {
  final proceed = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Kamera für QR-Code'),
      content: const Text(
        'Wachbuch benötigt die Kamera ausschließlich, um den QR-Code mit der '
        'Server-Adresse Ihrer Wache zu scannen. Ohne Kamera können Sie die '
        'Adresse auch manuell eingeben.',
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Abbrechen')),
        FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Weiter')),
      ],
    ),
  );
  if (proceed != true || !context.mounted) return null;

  final status = await Permission.camera.request();
  if (!context.mounted) return null;
  if (!status.isGranted) {
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kamera nicht freigegeben'),
        content: const Text(
          'Ohne Kamerazugriff können Sie den QR nicht scannen. '
          'Geben Sie die Server-Adresse manuell ein oder aktivieren Sie die '
          'Kamera in den Systemeinstellungen.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
          if (status.isPermanentlyDenied)
            FilledButton(
              onPressed: () {
                openAppSettings();
                Navigator.pop(ctx);
              },
              child: const Text('Einstellungen'),
            ),
        ],
      ),
    );
    return null;
  }

  return Navigator.of(context).push<String>(
    MaterialPageRoute(builder: (_) => const QrScanScreen()),
  );
}
