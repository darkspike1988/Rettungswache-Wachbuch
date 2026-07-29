import ipaddress
import socket
from urllib.parse import urlparse

import certifi
import urllib3


class UnsafeUrlError(ValueError):
    pass


def fetch_https(url, allowed_hosts, max_bytes, user_agent):
    """SSRF-gehaertetes HTTPS-GET: nur Port 443, nur erlaubte Hosts, nur
    global geroutete IP-Adressen, keine Weiterleitungen, begrenzte Groesse."""
    parsed_url = urlparse(url)
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in allowed_hosts
        or parsed_url.username
        or parsed_url.password
    ):
        raise UnsafeUrlError("URL ist nicht in der erlaubten HTTPS-Hostliste.")
    if parsed_url.port not in {None, 443}:
        raise UnsafeUrlError("Nur HTTPS-Port 443 ist erlaubt.")
    resolved = socket.getaddrinfo(parsed_url.hostname, 443, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(item[4][0] for item in resolved))
    if not addresses or any(not ipaddress.ip_address(value).is_global for value in addresses):
        raise UnsafeUrlError("Ziel zeigt nicht ausschliesslich auf globale IP-Adressen.")
    target = parsed_url.path or "/"
    if parsed_url.query:
        target = f"{target}?{parsed_url.query}"
    timeout = urllib3.Timeout(connect=5, read=20)
    connection_error = None
    for address in addresses:
        pool = urllib3.HTTPSConnectionPool(
            address,
            port=443,
            assert_hostname=parsed_url.hostname,
            server_hostname=parsed_url.hostname,
            cert_reqs="CERT_REQUIRED",
            ca_certs=certifi.where(),
            timeout=timeout,
            maxsize=1,
        )
        try:
            response = pool.request(
                "GET",
                target,
                headers={"Host": parsed_url.hostname, "User-Agent": user_agent},
                preload_content=False,
                redirect=False,
                retries=False,
            )
        except urllib3.exceptions.HTTPError as exc:
            connection_error = exc
            pool.close()
            continue
        try:
            if 300 <= response.status < 400:
                raise UnsafeUrlError("Weiterleitungen sind deaktiviert.")
            if response.status >= 400:
                raise UnsafeUrlError(f"Ziel antwortet mit HTTP {response.status}.")
            content = bytearray()
            for chunk in response.stream(64 * 1024):
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise UnsafeUrlError("Antwort ueberschreitet das Groessenlimit.")
            return bytes(content)
        finally:
            response.release_conn()
            pool.close()
    raise UnsafeUrlError(f"Ziel ist nicht erreichbar: {connection_error}")
