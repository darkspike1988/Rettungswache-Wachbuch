/// HTTP client for Wachbuch `/api/v1/` (Paperless/Nextcloud-style token auth).
library;

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

typedef WachbuchApiFactory = WachbuchApi Function(String baseUrl);

WachbuchApi defaultWachbuchApiFactory(String baseUrl) {
  return WachbuchApi(baseUrl: baseUrl);
}

class ApiException implements Exception {
  ApiException(this.statusCode, this.message, {this.code});

  final int statusCode;
  final String message;
  final String? code;

  bool get isMfaRequired =>
      statusCode == 403 && (code == 'mfa_required' || message.contains('MFA'));

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class AuthToken {
  const AuthToken({required this.value, this.expiresAt});

  final String value;
  final DateTime? expiresAt;
}

class WachbuchApi {
  WachbuchApi({
    required this.baseUrl,
    this.token,
    http.Client? client,
    this.requestTimeout = const Duration(seconds: 20),
  }) : _client = client ?? http.Client();

  /// Origin only, e.g. https://wache.example.org (no trailing slash).
  final String baseUrl;
  final String? token;
  final Duration requestTimeout;
  final http.Client _client;

  Uri _uri(String path) {
    final root = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    return Uri.parse('$root$path');
  }

  Map<String, String> _headers({bool auth = true}) {
    final headers = <String, String>{
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
    if (auth && token != null && token!.isNotEmpty) {
      headers['Authorization'] = 'Token $token';
    }
    return headers;
  }

  Future<http.Response> _send(Future<http.Response> request) async {
    try {
      return await request.timeout(requestTimeout);
    } on TimeoutException {
      throw ApiException(
        0,
        'Zeitlimit überschritten. Bitte Server und Verbindung prüfen.',
      );
    } on http.ClientException catch (error) {
      throw ApiException(0, 'Netzwerkfehler: ${error.message}');
    }
  }

  Map<String, dynamic> _decode(http.Response response) {
    Map<String, dynamic> body = {};
    if (response.body.isNotEmpty) {
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map<String, dynamic>) {
          body = decoded;
        } else {
          throw const FormatException('JSON object expected');
        }
      } on FormatException {
        if (response.statusCode >= 500) {
          throw ApiException(
            response.statusCode,
            'Serverfehler (${response.statusCode}). Bitte später erneut versuchen.',
          );
        }
        throw ApiException(
          response.statusCode,
          'Der Server hat eine ungültige Antwort gesendet.',
        );
      }
    }
    if (response.statusCode >= 400) {
      throw ApiException(
        response.statusCode,
        (body['error'] as String?) ??
            'Anfrage fehlgeschlagen (${response.statusCode})',
        code: body['code'] as String?,
      );
    }
    return body;
  }

  /// GET /api/v1/ – discovery without auth.
  Future<Map<String, dynamic>> discover() async {
    final response = await _send(
      _client.get(_uri('/api/v1/'), headers: _headers(auth: false)),
    );
    final body = _decode(response);
    ensureWachbuchDiscovery(body);
    return body;
  }

  /// POST /api/v1/token/
  Future<AuthToken> obtainToken({
    required String username,
    required String password,
    String label = 'Mobile App',
  }) async {
    final response = await _send(
      _client.post(
        _uri('/api/v1/token/'),
        headers: _headers(auth: false),
        body: jsonEncode({
          'username': username,
          'password': password,
          'label': label,
        }),
      ),
    );
    final body = _decode(response);
    final value = body['token'] as String?;
    if (value == null || value.isEmpty) {
      throw ApiException(response.statusCode, 'Kein Token in der Antwort.');
    }
    return AuthToken(
      value: value,
      expiresAt: _parseExpiresAt(body['expires_at']),
    );
  }

  /// GET /api/v1/me/
  Future<Map<String, dynamic>> me() async {
    final response = await _send(
      _client.get(_uri('/api/v1/me/'), headers: _headers()),
    );
    return _decode(response);
  }

  /// GET /api/v1/handovers/
  Future<List<Map<String, dynamic>>> handovers() async {
    final response = await _send(
      _client.get(_uri('/api/v1/handovers/'), headers: _headers()),
    );
    final body = _decode(response);
    final results = body['results'];
    if (results is! List) {
      return [];
    }
    return results
        .whereType<Map>()
        .map((entry) => Map<String, dynamic>.from(entry))
        .toList();
  }

  /// GET /api/v1/handovers/{id}/
  Future<Map<String, dynamic>> handoverDetail(int id) async {
    final response = await _send(
      _client.get(_uri('/api/v1/handovers/$id/'), headers: _headers()),
    );
    return _decode(response);
  }

  void close() {
    _client.close();
  }

  WachbuchApi copyWithToken(String newToken) {
    return WachbuchApi(
      baseUrl: baseUrl,
      token: newToken,
      client: _client,
      requestTimeout: requestTimeout,
    );
  }
}

/// Validates that a discovery payload looks like a Wachbuch API root.
void ensureWachbuchDiscovery(Map<String, dynamic> body) {
  final endpoints = body['endpoints'];
  final hasTokenEndpoint =
      endpoints is Map &&
      (endpoints.containsKey('token') || endpoints.containsKey('anmeldung'));
  final ok = body['ok'] == true || body['ok'] == 'true';
  final hasVersion =
      body['api_version'] != null ||
      body['version'] != null ||
      body['name'] != null;
  if (!ok && !hasTokenEndpoint && !hasVersion) {
    throw ApiException(
      0,
      'Die Adresse antwortet nicht wie ein Wachbuch-Server (/api/v1/).',
    );
  }
}

DateTime? _parseExpiresAt(Object? raw) {
  if (raw is! String || raw.isEmpty) return null;
  return DateTime.tryParse(raw)?.toLocal();
}

String normalizeServerUrl(String input) {
  var value = input.trim();
  if (value.isEmpty) {
    throw ArgumentError('Server-URL fehlt.');
  }
  if (!value.startsWith('http://') && !value.startsWith('https://')) {
    value = 'https://$value';
  }
  while (value.endsWith('/')) {
    value = value.substring(0, value.length - 1);
  }
  return value;
}

/// German labels for station module keys from `/me/`.
String moduleLabel(String key) {
  const labels = <String, String>{
    'calendar': 'Kalender',
    'birthdays': 'Geburtstage',
    'coffee': 'Kaffeekasse',
    'feeds': 'Meldungen & Verkehr',
    'checklists': 'Checklisten',
    'messaging': 'Nachrichten',
    'tasks': 'Aufgaben',
  };
  return labels[key] ?? key;
}
