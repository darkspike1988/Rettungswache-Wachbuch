import 'package:flutter_test/flutter_test.dart';
import 'package:wachbuch_mobile/models/kaffeekasse.dart';

void main() {
  group('Kaffeekasse', () {
    test('parses balance, currency, ledger and payment hint', () {
      final kasse = Kaffeekasse.fromJson({
        'balance': '42.50',
        'currency': 'EUR',
        'payment_hint': 'PayPal: paypal.me/wache',
        'ledger': [
          {
            'id': 1,
            'amount': '-2.00',
            'description': 'Kaffee',
            'user': {'display_name': 'Michael'},
            'created_at': '2026-08-02T10:00:00+00:00',
          },
          {
            'id': 2,
            'amount': '10.00',
            'description': 'Einzahlung',
            'member': 'Sandra',
            'date': '2026-08-01T08:00:00+00:00',
          },
        ],
      });

      expect(kasse.currency, 'EUR');
      expect(kasse.balance, contains('42'));
      expect(kasse.paymentHint, 'PayPal: paypal.me/wache');
      expect(kasse.ledger.length, 2);

      final first = kasse.ledger.first;
      expect(first.id, 1);
      expect(first.amount, -2.0);
      expect(first.isNegative, isTrue);
      expect(first.userName, 'Michael');
      expect(first.formattedAmount, startsWith('-'));
      expect(first.createdAt, isNotNull);

      final second = kasse.ledger.last;
      expect(second.amount, 10.0);
      expect(second.isNegative, isFalse);
      expect(second.userName, 'Sandra');
      expect(second.formattedAmount, startsWith('+'));
    });

    test('parses German decimal comma and saldo alias', () {
      final kasse = Kaffeekasse.fromJson({
        'saldo': '12,75',
      });

      expect(kasse.isNegative, isFalse);
      expect(kasse.ledger, isEmpty);
    });

    test('flags negative balances', () {
      final kasse = Kaffeekasse.fromJson({'balance': '-5.00'});

      expect(kasse.isNegative, isTrue);
    });

    test('parses mixed thousand and decimal separators', () {
      final kasse = Kaffeekasse.fromJson({'balance': '1.234,56'});

      expect(kasse.isNegative, isFalse);
    });

    test('is defensive about malformed amounts', () {
      final kasse = Kaffeekasse.fromJson({'balance': '---'});

      expect(kasse.isNegative, isFalse);
      expect(kasse.balance, isNotEmpty);
    });

    test('handles numeric balance and numeric entry amounts', () {
      final kasse = Kaffeekasse.fromJson({
        'balance': 9.99,
        'ledger': [
          {'id': 1, 'amount': -1, 'description': 'X'},
        ],
      });

      expect(kasse.ledger.first.amount, -1);
    });
  });
}
