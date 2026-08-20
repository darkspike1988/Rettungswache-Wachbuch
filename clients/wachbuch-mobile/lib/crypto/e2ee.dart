/// End-to-end encryption for Wachbuch messaging.
///
/// Byte-compatible with the web client (`core/static/core/app.js`) and the
/// server envelope format (`A256GCM+ECDH-ES`, see `docs/CRYPTO-BSI.md`):
///
/// * message body: AES-256-GCM (random 32-byte content key `CEK`, 12-byte nonce)
/// * per-recipient key wrap: ephemeral ECDH P-256 -> raw shared secret (X
///   coordinate) -> HKDF-SHA256(salt = 32x 0x00, info = "wachbuch-e2ee-v1",
///   len = 32) -> AES-256-GCM(12-byte IV) of the CEK
/// * private-key wrap: PBKDF2-SHA256 (>= 600k) -> AES-256-GCM(12-byte IV) of the
///   JSON-encoded private JWK
///
/// All binary values are base64url without padding. Implemented with the
/// pure-Dart `pointycastle` so it runs on device and under `flutter test`.
library;

import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:pointycastle/export.dart';

const String _hkdfInfo = 'wachbuch-e2ee-v1';
const int defaultKdfIterations = 600000;

final ECDomainParameters _p256 = ECCurve_secp256r1();

/// A freshly generated E2EE identity ready to register with the server.
class E2eeIdentity {
  const E2eeIdentity({
    required this.publicJwk,
    required this.privateJwk,
    required this.wrappedPrivateJwk,
    required this.kdfSalt,
    required this.kdfIterations,
  });

  final Map<String, dynamic> publicJwk;
  final Map<String, dynamic> privateJwk;
  final String wrappedPrivateJwk;
  final String kdfSalt;
  final int kdfIterations;
}

class E2eeException implements Exception {
  const E2eeException(this.message);
  final String message;
  @override
  String toString() => 'E2eeException: $message';
}

// --- base64url helpers ------------------------------------------------------

String _b64u(List<int> bytes) => base64Url.encode(bytes).replaceAll('=', '');

Uint8List _b64uDecode(String value) {
  final normalized = value.replaceAll('-', '+').replaceAll('_', '/');
  final pad = (4 - normalized.length % 4) % 4;
  return base64.decode(normalized + ('=' * pad));
}

// --- big-endian conversion --------------------------------------------------

Uint8List _bigIntTo32(BigInt value) {
  final out = Uint8List(32);
  var v = value;
  final mask = BigInt.from(0xff);
  for (var i = 31; i >= 0; i--) {
    out[i] = (v & mask).toInt();
    v = v >> 8;
  }
  return out;
}

BigInt _bytesToBigInt(List<int> bytes) {
  var result = BigInt.zero;
  for (final b in bytes) {
    result = (result << 8) | BigInt.from(b & 0xff);
  }
  return result;
}

// --- randomness -------------------------------------------------------------

final Random _sysRandom = Random.secure();

Uint8List _randomBytes(int length) {
  final bytes = Uint8List(length);
  for (var i = 0; i < length; i++) {
    bytes[i] = _sysRandom.nextInt(256);
  }
  return bytes;
}

SecureRandom _fortuna() {
  final fortuna = FortunaRandom();
  fortuna.seed(KeyParameter(_randomBytes(32)));
  return fortuna;
}

// --- key material -----------------------------------------------------------

AsymmetricKeyPair<PublicKey, PrivateKey> _generateEcKeyPair() {
  final generator = ECKeyGenerator()
    ..init(ParametersWithRandom(ECKeyGeneratorParameters(_p256), _fortuna()));
  return generator.generateKeyPair();
}

Map<String, dynamic> _publicJwk(ECPublicKey key) {
  final point = key.Q!;
  return {
    'kty': 'EC',
    'crv': 'P-256',
    'x': _b64u(_bigIntTo32(point.x!.toBigInteger()!)),
    'y': _b64u(_bigIntTo32(point.y!.toBigInteger()!)),
  };
}

ECPublicKey _publicFromJwk(Map<String, dynamic> jwk) {
  final x = _bytesToBigInt(_b64uDecode(jwk['x'] as String));
  final y = _bytesToBigInt(_b64uDecode(jwk['y'] as String));
  return ECPublicKey(_p256.curve.createPoint(x, y), _p256);
}

ECPrivateKey _privateFromJwk(Map<String, dynamic> jwk) {
  final d = _bytesToBigInt(_b64uDecode(jwk['d'] as String));
  return ECPrivateKey(d, _p256);
}

// --- primitives -------------------------------------------------------------

/// Raw ECDH shared secret = X coordinate of the shared point (32 bytes),
/// identical to Web Crypto `deriveBits({name:"ECDH"}, ..., 256)`.
Uint8List _ecdhSharedSecret(ECPrivateKey priv, ECPublicKey pub) {
  final agreement = ECDHBasicAgreement()..init(priv);
  return _bigIntTo32(agreement.calculateAgreement(pub));
}

Uint8List _hkdfSha256(Uint8List ikm) {
  final hkdf = HKDFKeyDerivator(SHA256Digest())
    ..init(HkdfParameters(ikm, 32, Uint8List(32), utf8.encode(_hkdfInfo)));
  return hkdf.process(Uint8List(0));
}

Uint8List _pbkdf2Sha256(String passphrase, Uint8List salt, int iterations) {
  final derivator = PBKDF2KeyDerivator(HMac(SHA256Digest(), 64))
    ..init(Pbkdf2Parameters(salt, iterations, 32));
  return derivator.process(Uint8List.fromList(utf8.encode(passphrase)));
}

Uint8List _gcmEncrypt(Uint8List key, Uint8List iv, Uint8List plaintext) {
  final cipher = GCMBlockCipher(AESEngine())
    ..init(true, AEADParameters(KeyParameter(key), 128, iv, Uint8List(0)));
  return cipher.process(plaintext);
}

Uint8List _gcmDecrypt(Uint8List key, Uint8List iv, Uint8List ciphertext) {
  final cipher = GCMBlockCipher(AESEngine())
    ..init(false, AEADParameters(KeyParameter(key), 128, iv, Uint8List(0)));
  return cipher.process(ciphertext);
}

// --- public API -------------------------------------------------------------

class E2ee {
  const E2ee._();

  /// Generate a P-256 identity and wrap its private key with [passphrase].
  static E2eeIdentity generateIdentity(String passphrase) {
    final pair = _generateEcKeyPair();
    final publicKey = pair.publicKey as ECPublicKey;
    final privateKey = pair.privateKey as ECPrivateKey;
    final publicJwk = _publicJwk(publicKey);
    final privateJwk = <String, dynamic>{
      ...publicJwk,
      'd': _b64u(_bigIntTo32(privateKey.d!)),
    };
    final salt = _randomBytes(16);
    final kek = _pbkdf2Sha256(passphrase, salt, defaultKdfIterations);
    final iv = _randomBytes(12);
    final wrapped = _gcmEncrypt(kek, iv, Uint8List.fromList(utf8.encode(jsonEncode(privateJwk))));
    return E2eeIdentity(
      publicJwk: publicJwk,
      privateJwk: privateJwk,
      wrappedPrivateJwk: '${_b64u(iv)}.${_b64u(wrapped)}',
      kdfSalt: _b64u(salt),
      kdfIterations: defaultKdfIterations,
    );
  }

  /// Recover the private JWK from a passphrase-wrapped bundle.
  static Map<String, dynamic> unlockIdentity({
    required String wrappedPrivateJwk,
    required String kdfSalt,
    required int kdfIterations,
    required String passphrase,
  }) {
    final parts = wrappedPrivateJwk.split('.');
    if (parts.length != 2 || parts[0].isEmpty || parts[1].isEmpty) {
      throw const E2eeException('Gespeicherter Schluesselumschlag ist beschaedigt.');
    }
    final kek = _pbkdf2Sha256(passphrase, _b64uDecode(kdfSalt), kdfIterations);
    final Uint8List plain;
    try {
      plain = _gcmDecrypt(kek, _b64uDecode(parts[0]), _b64uDecode(parts[1]));
    } on Object {
      throw const E2eeException('Falsche Passphrase oder beschaedigter Schluessel.');
    }
    return jsonDecode(utf8.decode(plain)) as Map<String, dynamic>;
  }

  /// Encrypt [plaintext] for a list of `{user_id, public_jwk}` recipients.
  /// Recipients without a public key are skipped (they cannot read the message).
  static Map<String, dynamic> encryptForRecipients(
    String plaintext,
    List<Map<String, dynamic>> recipients,
  ) {
    final cek = _randomBytes(32);
    final nonce = _randomBytes(12);
    final ciphertext = _gcmEncrypt(cek, nonce, Uint8List.fromList(utf8.encode(plaintext)));
    final keyWraps = <String, dynamic>{};
    for (final recipient in recipients) {
      final publicJwk = recipient['public_jwk'];
      if (publicJwk == null) continue;
      final userId = recipient['user_id'];
      keyWraps[userId.toString()] =
          _wrapForRecipient(cek, Map<String, dynamic>.from(publicJwk as Map));
    }
    return {
      'ciphertext': _b64u(ciphertext),
      'nonce': _b64u(nonce),
      'key_wraps': keyWraps,
    };
  }

  /// Decrypt a server envelope with the viewer's private JWK.
  /// Legacy plaintext rows (`is_encrypted == false`) return their body.
  static String decryptEnvelope(
    Map<String, dynamic> envelope,
    Map<String, dynamic> privateJwk,
  ) {
    if (envelope['is_encrypted'] == false) {
      return (envelope['legacy_body'] ?? '').toString();
    }
    final wrap = envelope['wrap'];
    if (wrap == null) {
      throw const E2eeException('Kein Schluesselumschlag fuer dich - Nachricht nicht lesbar.');
    }
    final cek = _unwrapKey(Map<String, dynamic>.from(wrap as Map), privateJwk);
    final plain = _gcmDecrypt(
      cek,
      _b64uDecode(envelope['nonce'] as String),
      _b64uDecode(envelope['ciphertext'] as String),
    );
    return utf8.decode(plain);
  }
}

Map<String, dynamic> _wrapForRecipient(Uint8List cek, Map<String, dynamic> recipientPublicJwk) {
  final ephemeral = _generateEcKeyPair();
  final ePriv = ephemeral.privateKey as ECPrivateKey;
  final ePub = ephemeral.publicKey as ECPublicKey;
  final shared = _ecdhSharedSecret(ePriv, _publicFromJwk(recipientPublicJwk));
  final kek = _hkdfSha256(shared);
  final iv = _randomBytes(12);
  final wrapped = _gcmEncrypt(kek, iv, cek);
  return {
    'epk': _publicJwk(ePub),
    'wrapped_key': '${_b64u(iv)}.${_b64u(wrapped)}',
  };
}

Uint8List _unwrapKey(Map<String, dynamic> wrap, Map<String, dynamic> privateJwk) {
  final priv = _privateFromJwk(privateJwk);
  final epk = _publicFromJwk(Map<String, dynamic>.from(wrap['epk'] as Map));
  final shared = _ecdhSharedSecret(priv, epk);
  final kek = _hkdfSha256(shared);
  final parts = (wrap['wrapped_key'] as String).split('.');
  if (parts.length != 2) {
    throw const E2eeException('Schluesselumschlag ungueltig.');
  }
  return _gcmDecrypt(kek, _b64uDecode(parts[0]), _b64uDecode(parts[1]));
}
