import 'package:flutter_test/flutter_test.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/api/server_address.dart';

void main() {
  test('normalizeServerUrl adds https and strips slash', () {
    expect(normalizeServerUrl('wache.example.org/'), 'https://wache.example.org');
    expect(normalizeServerUrl('https://wache.example.org'), 'https://wache.example.org');
  });

  test('parseServerAddress strips path to origin', () {
    expect(
      parseServerAddress('https://wache.example.org/anmelden/'),
      'https://wache.example.org',
    );
  });

  test('parseServerAddress accepts JSON and deep link', () {
    expect(
      parseServerAddress('{"url":"https://wache.example.org"}'),
      'https://wache.example.org',
    );
    expect(
      parseServerAddress('wachbuch://connect?url=https%3A%2F%2Fwache.example.org'),
      'https://wache.example.org',
    );
  });
}
