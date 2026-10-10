FROM caddy:2.11.4-alpine
# Serving on 8080 needs no privileged-port file capability.
# Remove the upstream file capability so cap_drop ALL permits exec.
RUN setcap -r /usr/bin/caddy
COPY dist/ /srv/
COPY Caddyfile /etc/caddy/Caddyfile
USER 65532:65532
EXPOSE 8080
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
