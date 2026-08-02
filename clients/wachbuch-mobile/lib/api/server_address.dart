/// Parse and normalize Wachbuch server addresses from typed input or QR payloads.
library;

import 'dart:convert';

import 'package:wachbuch_mobile/api/client.dart';

/// Extracts a Wachbuch server origin from typed text or QR content.
///
/// Accepted forms (Google Play / Nextcloud-style self-host setup):
/// - `https://wache.example.org`
/// - `wache.example.org` (https assumed)
/// - `https://wache.example.org/anmelden/` (path stripped to origin)
/// - JSON: `{"url":"https://…"}` or `{"server":"https://…"}`
/// - `wachbuch://connect?url=https%3A%2F%2F…`
String parseServerAddress(String raw) {
  var value = raw.trim();
  if (value.isEmpty) {
    throw ArgumentError('Adresse fehlt.');
  }

  if (value.startsWith('{')) {
    final decoded = jsonDecode(value);
    if (decoded is Map) {
      final url = decoded['url'] ?? decoded['server'] ?? decoded['baseUrl'];
      if (url is String && url.trim().isNotEmpty) {
        value = url.trim();
      }
    }
  }

  final deepLink = Uri.tryParse(value);
  if (deepLink != null &&
      deepLink.scheme == 'wachbuch' &&
      (deepLink.host == 'connect' || deepLink.path.contains('connect'))) {
    final url = deepLink.queryParameters['url'];
    if (url != null && url.isNotEmpty) {
      value = url;
    }
  }

  final normalized = normalizeServerUrl(value);
  final uri = Uri.parse(normalized);
  if (uri.host.isEmpty) {
    throw ArgumentError('Ungültige Server-Adresse.');
  }
  final port = uri.hasPort ? ':${uri.port}' : '';
  return '${uri.scheme}://${uri.host}$port';
}
