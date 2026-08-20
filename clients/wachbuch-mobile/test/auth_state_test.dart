import 'package:flutter_test/flutter_test.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/state/auth_state.dart';

class _FakeApi extends WachbuchApi {
  _FakeApi(this._result)
    : super(baseUrl: 'https://wache.example.org', token: 'wb_test');

  final Object _result;

  @override
  Future<Map<String, dynamic>> me() async {
    if (_result is Exception) throw _result;
    return Map<String, dynamic>.from(_result as Map);
  }
}

Map<String, dynamic> _mePayload({String stationName = 'Rettungswache Test'}) {
  return {
    'user': {'username': 'michael'},
    'membership': {
      'role_label': 'Schichtleitung',
      'station': {
        'name': stationName,
        'modules': {'coffee': true, 'calendar': false},
      },
    },
  };
}

void main() {
  test('reload() populates me and notifies listeners', () async {
    final api = _FakeApi(_mePayload());
    final state = AuthState(api: api);

    var notifications = 0;
    state.addListener(() => notifications++);

    expect(state.loading, isFalse);
    expect(state.me, isNull);

    final future = state.reload();
    expect(state.loading, isTrue);
    await future;

    expect(state.loading, isFalse);
    expect(state.error, isNull);
    expect(state.me?['user']['username'], 'michael');
    expect(notifications, greaterThanOrEqualTo(2));
    state.dispose();
  });

  test('reload() stores error message and status on API failure', () async {
    final api = _FakeApi(ApiException(401, 'Token ungültig'));
    final state = AuthState(api: api);

    await state.reload();

    expect(state.loading, isFalse);
    expect(state.me, isNull);
    expect(state.error, contains('Token ungültig'));
    expect(state.lastError?.statusCode, 401);
    state.dispose();
  });

  test('stationName, roleLabel and modules resolve from membership', () async {
    final api = _FakeApi(_mePayload(stationName: 'Wache Nord'));
    final state = AuthState(api: api);
    await state.reload();

    expect(state.stationName('Wachbuch'), 'Wache Nord');
    expect(state.roleLabel, 'Schichtleitung');
    expect(state.modules['coffee'], isTrue);
    expect(state.username, 'michael');
    expect(state.hasData, isTrue);
    state.dispose();
  });

  test('username falls back to top-level me.username', () async {
    final api = _FakeApi(<String, dynamic>{
      'username': 'demo-schicht',
      'membership': {
        'role_label': 'Schichtleitung',
        'station': {'name': 'RW', 'modules': {}},
      },
    });
    final state = AuthState(api: api);
    await state.reload();
    expect(state.username, 'demo-schicht');
    state.dispose();
  });

  test('stationName falls back when membership is absent', () async {
    final api = _FakeApi(<String, dynamic>{
      'user': {'username': 'x'},
    });
    final state = AuthState(api: api);
    await state.reload();

    expect(state.stationName('Wachbuch'), 'Wachbuch');
    expect(state.roleLabel, '');
    expect(state.modules, isEmpty);
    state.dispose();
  });
}
