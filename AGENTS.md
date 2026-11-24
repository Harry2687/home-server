# Home Server Agent Rules

## Docker Network Subnets

- **Never pin static Docker subnets in `172.17.0.0/16`–`172.31.0.0/16`.** That range is Docker's default auto-allocation pool. Because `scripts/backup_appdata.sh` runs `docker compose down` and `docker compose up -d` daily, Compose creates networks in parallel and unpinned networks (`security-network`, `media-network`, `immich-network`, `home-server_default`) will race and collide with any pinned `172.x` subnet, leaving all containers down.
- **Allocate static subnets in `10.2x.0.0/24`** using the next unused block:
  - `10.25.0.0/24` — `minecraft-network` (`compose/mc/docker-compose.yml`)
  - `10.26.0.0/24` — `bitmagnet-network` (`compose/p2p/docker-compose.yml`)
  - `10.27.0.0/24` — `proxy-network` (`docker-compose.yml`)
- **Update dependent app configs when changing `proxy-network`:** check and update trusted-proxy CIDRs (such as `appdata/jellyfin/config/network.xml` `<KnownProxies>`) to match the new subnet.
- **Verify network changes with a cold recreation:** test with `docker compose down && docker compose up -d --remove-orphans` (not just `up -d` on existing networks) so parallel network creation matches the daily backup cycle.

## Non-Obvious Constraints

- **Keep Jellyfin port `8096:8096` exposed on the host** (`compose/media/docker-compose.yml`): even though other reverse-proxied services intentionally omit host `ports:`, Jellyfin needs direct port `8096` access for Google TV.
- **Keep Gluetun's `HEALTH_SUCCESS_WAIT_DURATION=99999h` and `condition: service_started`** (`compose/p2p/docker-compose.yml`): do not change this back to periodic health checks or `service_healthy` — frequent Gluetun health checks previously caused VPN disconnections.
- **Keep Caddy's explicit public DNS (`1.1.1.1`, `8.8.8.8`)** in both `compose/network/docker-compose.yml` and `compose/network/caddy_conf/Caddyfile` TLS blocks: required to bypass local AdGuard split-horizon DNS during ACME DNS-01 challenges.
- **Tailscale runs as a host `systemd` service, not a Docker container:** do not try to manage or re-add it via Docker Compose.
