/// Holds the unlocked E2EE private key for the current app session only.
///
/// Mirrors the web client, which keeps the decrypted private JWK in
/// `sessionStorage`: it lives in memory, is never written to disk, and is
/// cleared on logout. Persisting it would weaken the passphrase protection.
library;

class CryptoSession {
  CryptoSession();

  /// Process-wide session used by the app shell; tests inject their own.
  static final CryptoSession instance = CryptoSession();

  Map<String, dynamic>? _privateJwk;

  bool get isUnlocked => _privateJwk != null;

  Map<String, dynamic>? get privateJwk => _privateJwk;

  void unlockWith(Map<String, dynamic> privateJwk) {
    _privateJwk = privateJwk;
  }

  void lock() {
    _privateJwk = null;
  }
}
