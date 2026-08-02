import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Persists server URL (prefs) and API token (secure storage).
class SessionStore {
  SessionStore({
    FlutterSecureStorage? secureStorage,
  }) : _secure = secureStorage ?? const FlutterSecureStorage();

  static const _urlKey = 'wachbuch_server_url';
  static const _tokenKey = 'wachbuch_api_token';

  final FlutterSecureStorage _secure;

  Future<String?> readServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_urlKey);
  }

  Future<void> writeServerUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_urlKey, url);
  }

  Future<String?> readToken() => _secure.read(key: _tokenKey);

  Future<void> writeToken(String token) => _secure.write(key: _tokenKey, value: token);

  Future<void> clearToken() => _secure.delete(key: _tokenKey);

  Future<void> clearAll() async {
    await clearToken();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_urlKey);
  }
}
