from django.test import RequestFactory, TestCase, override_settings

from .middleware import ClientIPMiddleware
from .rate_limit import consume, hash_key


class ClientIPMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, **meta):
        return self.factory.get("/", **meta)

    @override_settings(TRUSTED_PROXY=False)
    def test_no_proxy_uses_remote_addr(self):
        request = self._request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        ClientIPMiddleware(lambda r: r)(request)
        self.assertEqual(request.client_ip, "10.0.0.1")

    @override_settings(TRUSTED_PROXY=True)
    def test_trusted_proxy_uses_x_forwarded_for(self):
        request = self._request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.1")
        ClientIPMiddleware(lambda r: r)(request)
        self.assertEqual(request.client_ip, "1.2.3.4")

    @override_settings(TRUSTED_PROXY=True)
    def test_trusted_proxy_with_oversize_ip_falls_back(self):
        request = self._request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="x" * 200)
        ClientIPMiddleware(lambda r: r)(request)
        self.assertEqual(request.client_ip, "unknown")

    def test_missing_remote_addr_returns_unknown(self):
        request = self._request()
        ClientIPMiddleware(lambda r: r)(request)
        self.assertIn(request.client_ip, ["unknown", "127.0.0.1"])


class RateLimitConsumeTests(TestCase):
    @override_settings(RATELIMIT_KEY_SALT="test-salt")
    def test_consume_returns_true_within_limit(self):
        for _ in range(3):
            self.assertTrue(consume("test-bucket", "k1", limit=3, window_seconds=60))

    @override_settings(RATELIMIT_KEY_SALT="test-salt")
    def test_consume_returns_false_over_limit(self):
        for _ in range(2):
            consume("test-bucket-over", "k1", limit=2, window_seconds=60)
        self.assertFalse(consume("test-bucket-over", "k1", limit=2, window_seconds=60))

    @override_settings(RATELIMIT_KEY_SALT="test-salt")
    def test_consume_isolates_per_key(self):
        for _ in range(2):
            consume("test-bucket-isolate", "kA", limit=2, window_seconds=60)
        self.assertTrue(consume("test-bucket-isolate", "kB", limit=2, window_seconds=60))

    @override_settings(RATELIMIT_KEY_SALT="test-salt")
    def test_consume_isolates_per_bucket(self):
        consume("test-bucket-X", "k1", limit=1, window_seconds=60)
        self.assertTrue(consume("test-bucket-Y", "k1", limit=1, window_seconds=60))

    def test_hash_key_uses_salt(self):
        with override_settings(RATELIMIT_KEY_SALT="salt-A"):
            hash_a = hash_key("k1")
        with override_settings(RATELIMIT_KEY_SALT="salt-B"):
            hash_b = hash_key("k1")
        self.assertNotEqual(hash_a, hash_b)
        self.assertEqual(len(hash_a), 64)
