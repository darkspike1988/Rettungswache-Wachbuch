import 'package:flutter_test/flutter_test.dart';
import 'package:wachbuch_mobile/api/client.dart';

void main() {
  test('normalizeServerUrl adds https and strips slash', () {
    expect(normalizeServerUrl('wache.example.org/'), 'https://wache.example.org');
    expect(normalizeServerUrl('https://wache.example.org'), 'https://wache.example.org');
  });
}
