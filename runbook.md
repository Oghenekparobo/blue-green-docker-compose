## 🔄 Failover Alert

**What**: Blue/Green switched (e.g., Blue died).
**Do**:

1. `docker compose logs app_blue` (check errors).
2. Restart: `docker compose restart app_blue`.
3. Traffic auto-fixes.

## ⚠️ High Errors

**What**: Too many 500s (>2% in 200 requests).
**Do**:

1. `docker compose logs nginx | grep upstream_status=5`.
2. Check app: `docker compose logs app_green`.
3. Force switch: `docker compose stop app_blue`.

## Recovery

Healthy = no alerts. Watch: `docker compose logs -f alert_watcher`.
