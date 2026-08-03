import 'package:flutter_test/flutter_test.dart';
import 'package:wachbuch_mobile/api/client.dart';

void main() {
  test('moduleLabel maps known keys to German names', () {
    expect(moduleLabel('coffee'), 'Kaffeekasse');
    expect(moduleLabel('calendar'), 'Kalender');
    expect(moduleLabel('checklists'), 'Checklisten');
    expect(moduleLabel('custom_module'), 'custom_module');
  });

  test('ensureWachbuchDiscovery accepts ok endpoints payloads', () {
    expect(
      () => ensureWachbuchDiscovery({
        'ok': true,
        'endpoints': {'token': '/api/v1/token/'},
      }),
      returnsNormally,
    );
  });

  test('ensureWachbuchDiscovery rejects unrelated JSON', () {
    expect(
      () => ensureWachbuchDiscovery({'status': 'up'}),
      throwsA(isA<ApiException>()),
    );
  });
}
