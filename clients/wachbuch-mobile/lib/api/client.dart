/// HTTP client for Wachbuch `/api/v1/` (Paperless/Nextcloud-style token auth).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  ApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class WachbuchApi {
  WachbuchApi({
    required this.baseUrl,
    this.token,
    http.Client? client,
  }) : _client = client ?? http.Client();

  /// Origin only, e.g. https://wache.example.org (no trailing slash).
  final String baseUrl;
  final String? token;
  final http.Client _client;

  Uri _uri(String path) {
    final root = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
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

  Future<Map<String, dynamic>> _decode(http.Response response) {
    Map<String, dynamic> body = {};
    if (response.body.isNotEmpty) {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        body = decoded;
      }
    }
    if (response.statusCode >= 400) {
      throw ApiException(
        response.statusCode,
        (body['error'] as String?) ?? 'Anfrage fehlgeschlagen (${response.statusCode})',
      );
    }
    return Future.value(body);
  }

  /// GET /api/v1/ – discovery without auth.
  Future<Map<String, dynamic>> discover() async {
    final response = await _client.get(_uri('/api/v1/'), headers: _headers(auth: false));
    return _decode(response);
  }

  /// POST /api/v1/token/
  Future<String> obtainToken({
    required String username,
    required String password,
    String label = 'Mobile App',
  }) async {
    final response = await _client.post(
      _uri('/api/v1/token/'),
      headers: _headers(auth: false),
      body: jsonEncode({
        'username': username,
        'password': password,
        'label': label,
      }),
    );
    final body = await _decode(response);
    final value = body['token'] as String?;
    if (value == null || value.isEmpty) {
      throw ApiException(response.statusCode, 'Kein Token in der Antwort.');
    }
    return value;
  }

  /// GET /api/v1/me/
  Future<Map<String, dynamic>> me() async {
    final response = await _client.get(_uri('/api/v1/me/'), headers: _headers());
    return _decode(response);
  }

  /// GET /api/v1/handovers/
  Future<List<Map<String, dynamic>>> handovers() async {
    final response = await _client.get(_uri('/api/v1/handovers/'), headers: _headers());
    final body = await _decode(response);
    final results = body['results'];
    if (results is! List) {
      return [];
    }
    return results.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
  }

  WachbuchApi copyWithToken(String newToken) {
    return WachbuchApi(baseUrl: baseUrl, token: newToken, client: _client);
  }
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
