import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wachbuch_mobile/crypto/e2ee.dart';

/// Interop vector produced by the reference implementation of the web/server
/// scheme (Python `cryptography`, identical primitives to `app.js`). The Dart
/// implementation must consume these exact bytes. See scripts/crypto_ref.py in
/// the server repo for how the vector is generated.
const Map<String, dynamic> _recipientPrivateJwk = {
  'kty': 'EC',
  'crv': 'P-256',
  'x': 'AZQtv9vAQ-cNiNrOIXNMnoltPWutBNOBKBaT-vVGU1M',
  'y': 'X-eE4z_DhcDRcTARZ7-_DM0KtrG4dnc3M9lFEJAJFa0',
  'd': 'iDvAFh2kA0hYX7FJk7scKjwJkLatZBpd1u8Au-0t_pQ',
};

const Map<String, dynamic> _vectorEnvelope = {
  'ciphertext': 'V8woNRaGoX-0Ckc5NgQFROTV9HZtZtfp70Rwanu5AxwvWiE96JIQ',
  'nonce': '-4j6osdcu5FG29dP',
  'wrap': {
    'epk': {
      'kty': 'EC',
      'crv': 'P-256',
      'x': 'kCK-K01UKiieaRjWIkWE_LC5brbDJoPi_Y6-mZpfmoI',
      'y': 'RhXTxpSNGAHhP8Eo8x6wU82HgHDWiAw564-_XbNRr6E',
    },
    'wrapped_key':
        'W764t3Ib-bLeL_7l.OmkgAYmJa1QtPQyhhZUzzCUTCXRjZxai-WLiDX6S0x-686I-x6OaE1ui7u9rG-ZL',
  },
  'is_encrypted': true,
};

const String _vectorPlaintext = 'Hallo Wache - E2EE Test';
const String _vectorPassphrase = 'geheime-passphrase-123';
const String _vectorWrappedPrivateJwk =
    'Z_A6DPrOotSc9XoK.2knn7KOS4e3ru7xuNnFm9YozNFSAV9_Tbo_tVL6XbfXO5jtM4Ur24t0HTkLgkbRac_OGlq88jRL0ZyUt9vvGIWg7cldxfHMoBjEy_xMobtUkOZt1mt-DTyorZMXokcXeJxgCT3QmDHRCqnAciL2stgeDBBcsM4lsssSV50jxpqiKsMYroRVZp4fYYdtmJFp6Jo5AiP8WL7nTucS0rMfd6UivGwCwcvrIi5jhYUemS7cdTfZEyek5SdOzned1NOHibY76-fchIcac';
const String _vectorKdfSalt = 'XNHX0iGeLdemhxsc1uG_jw';
const int _vectorKdfIterations = 600000;

void main() {
  group('E2ee interop with the web/server scheme', () {
    test('decrypts a reference envelope produced by the Python/JS scheme', () {
      final plaintext = E2ee.decryptEnvelope(
        Map<String, dynamic>.from(_vectorEnvelope),
        Map<String, dynamic>.from(_recipientPrivateJwk),
      );
      expect(plaintext, _vectorPlaintext);
    });

    test('unlocks a reference passphrase-wrapped private key', () {
      final privateJwk = E2ee.unlockIdentity(
        wrappedPrivateJwk: _vectorWrappedPrivateJwk,
        kdfSalt: _vectorKdfSalt,
        kdfIterations: _vectorKdfIterations,
        passphrase: _vectorPassphrase,
      );
      expect(privateJwk['d'], _recipientPrivateJwk['d']);
      expect(privateJwk['x'], _recipientPrivateJwk['x']);
      expect(privateJwk['y'], _recipientPrivateJwk['y']);
    });

    test('unlock with a wrong passphrase throws', () {
      expect(
        () => E2ee.unlockIdentity(
          wrappedPrivateJwk: _vectorWrappedPrivateJwk,
          kdfSalt: _vectorKdfSalt,
          kdfIterations: _vectorKdfIterations,
          passphrase: 'falsch',
        ),
        throwsA(isA<E2eeException>()),
      );
    });
  });

  group('E2ee round-trip', () {
    test('generateIdentity -> encrypt -> decrypt recovers the plaintext', () {
      final identity = E2ee.generateIdentity('meine-passphrase');
      const message = 'Übergabe: RTW 1 einsatzklar 🚑';
      final payload = E2ee.encryptForRecipients(message, [
        {'user_id': 7, 'public_jwk': identity.publicJwk},
      ]);
      final envelope = {
        'is_encrypted': true,
        'ciphertext': payload['ciphertext'],
        'nonce': payload['nonce'],
        'wrap': (payload['key_wraps'] as Map)['7'],
      };
      final recovered = E2ee.decryptEnvelope(envelope, identity.privateJwk);
      expect(recovered, message);
    });

    test('unlock after generateIdentity yields a usable private key', () {
      final identity = E2ee.generateIdentity('pw-123456');
      final unlocked = E2ee.unlockIdentity(
        wrappedPrivateJwk: identity.wrappedPrivateJwk,
        kdfSalt: identity.kdfSalt,
        kdfIterations: identity.kdfIterations,
        passphrase: 'pw-123456',
      );
      expect(unlocked['d'], identity.privateJwk['d']);
    });

    test('encrypts for multiple recipients, each can decrypt', () {
      final alex = E2ee.generateIdentity('a');
      final mara = E2ee.generateIdentity('b');
      const message = 'Gruppeninfo';
      final payload = E2ee.encryptForRecipients(message, [
        {'user_id': 1, 'public_jwk': alex.publicJwk},
        {'user_id': 2, 'public_jwk': mara.publicJwk},
      ]);
      final wraps = payload['key_wraps'] as Map;
      expect(wraps.keys.toSet(), {'1', '2'});
      for (final entry in [
        [alex, '1'],
        [mara, '2'],
      ]) {
        final identity = entry[0] as E2eeIdentity;
        final envelope = {
          'is_encrypted': true,
          'ciphertext': payload['ciphertext'],
          'nonce': payload['nonce'],
          'wrap': wraps[entry[1]],
        };
        expect(E2ee.decryptEnvelope(envelope, identity.privateJwk), message);
      }
    });

    test('legacy plaintext envelope returns its body', () {
      final plain = E2ee.decryptEnvelope(
        {'is_encrypted': false, 'legacy_body': 'alter Klartext'},
        Map<String, dynamic>.from(_recipientPrivateJwk),
      );
      expect(plain, 'alter Klartext');
    });
  });

  test('writes a Dart-produced envelope for the Python cross-check', () {
    const message = 'Dart erzeugt, Referenz liest';
    final payload = E2ee.encryptForRecipients(message, [
      {'user_id': 1, 'public_jwk': Map<String, dynamic>.from(_recipientPrivateJwk)},
    ]);
    final envelope = {
      'is_encrypted': true,
      'ciphertext': payload['ciphertext'],
      'nonce': payload['nonce'],
      'wrap': (payload['key_wraps'] as Map)['1'],
    };
    final outPath = Platform.environment['DART_ENVELOPE_OUT'] ?? '/tmp/dart_envelope.json';
    File(outPath).writeAsStringSync(jsonEncode({
      'plaintext': message,
      'envelope': envelope,
      'private_jwk': _recipientPrivateJwk,
    }));
    // Self-consistency: Dart can read back its own output.
    expect(
      E2ee.decryptEnvelope(envelope, Map<String, dynamic>.from(_recipientPrivateJwk)),
      message,
    );
  });
}
