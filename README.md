# Blue/Green Deployment with Nginx Auto-Failover

## 📋 Overview

This project implements a Blue/Green deployment strategy for a Node.js application using Nginx as a reverse proxy with automatic failover capabilities. When the active pool (Blue) fails, Nginx automatically routes traffic to the backup pool (Green) with zero downtime.

## 🏗️ Architecture

```
                    ┌─────────────────┐
                    │   Port 8080     │
                    │     Nginx       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Active Pool    │
                    │   Routing       │
                    └────┬──────┬─────┘
                         │      │
              ┌──────────▼─┐  ┌─▼──────────┐
              │   Blue     │  │   Green    │
              │ (Primary)  │  │  (Backup)  │
              │ Port 8081  │  │ Port 8082  │
              └────────────┘  └────────────┘
```

## 🎯 Key Features

- ✅ **Zero-downtime failover**: Automatic switch from Blue to Green on failure
- ✅ **Health-based routing**: Nginx monitors upstream health
- ✅ **Fast failure detection**: 2-second timeouts with immediate retry
- ✅ **Header preservation**: `X-App-Pool` and `X-Release-Id` forwarded to clients
- ✅ **Chaos testing**: Simulate failures with `/chaos/*` endpoints
- ✅ **Fully parameterized**: All configuration via `.env` file

## 📦 Repository Structure

```
.
├── docker-compose.yml          # Container orchestration
├── nginx.conf.template         # Nginx configuration template
├── .env.example               # Environment variables template
├── .env                       # Your local environment (not committed)
├── README.md                  # This file
└── DECISION.md               # Implementation decisions (optional)
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/stage-2-blue-green.git
cd stage-2-blue-green

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

The `.env` file should contain:

```properties
BLUE_IMAGE=
GREEN_IMAGE=
RELEASE_ID_BLUE=
RELEASE_ID_GREEN=
ACTIVE_POOL=
APP_PORT=
```

### 3. Start Services

```bash
# Start all containers
docker-compose up -d

# Wait for health checks to pass
sleep 10

# Verify containers are healthy
docker-compose ps
```

Expected output:

```
NAME                             STATUS
stage-2-blue-green-app_blue-1    Up (healthy)
stage-2-blue-green-app_green-1   Up (healthy)
stage-2-blue-green-nginx-1       Up
```

## 🧪 Testing & Verification

### Test 1: Verify Normal Operation (Blue Active)

```bash
# Test through Nginx
curl -i http://localhost:8080/version

# Expected response headers:
# X-App-Pool: blue
# X-Release-Id: blue-v1.0.0
# HTTP/1.1 200 OK
```

### Test 2: Direct Container Access

```bash
# Test Blue directly (bypass Nginx)
curl -i http://localhost:8081/version

# Test Green directly (bypass Nginx)
curl -i http://localhost:8082/version

# Health checks
curl http://localhost:8081/healthz
curl http://localhost:8082/healthz
```

### Test 3: Chaos Testing & Automatic Failover

```bash
# Step 1: Verify Blue is active
curl -i http://localhost:8080/version
# Should show: X-App-Pool: blue

# Step 2: Trigger failure on Blue
curl -X POST "http://localhost:8081/chaos/start?mode=error"
# Response: {"message":"Simulation mode 'error' activated"}

# Step 3: Test automatic failover
curl -i http://localhost:8080/version
# Should now show: X-App-Pool: green (automatic switch!)

# Step 4: Verify stability (all requests should return 200)
for i in {1..10}; do
  echo "Request $i: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/version)"
done

# Step 5: Stop chaos simulation
curl -X POST "http://localhost:8081/chaos/stop"
# Response: {"message":"Simulation stopped"}

# Step 6: Verify Blue is back in rotation
curl -i http://localhost:8080/version
# Should show: X-App-Pool: blue (back to normal)
```

### Test 4: Load Testing During Failover

```bash
# Run continuous requests while triggering chaos
# Terminal 1: Start load test
while true; do
  curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8080/version
  sleep 0.5
done

# Terminal 2: Trigger chaos
curl -X POST "http://localhost:8081/chaos/start?mode=error"

# Observe: No 500 errors, seamless transition to Green
```

## 🔧 Configuration Details

### Environment Variables

| Variable           | Description                       | Example                                |
| ------------------ | --------------------------------- | -------------------------------------- |
| `BLUE_IMAGE`       | Docker image for Blue pool        | `yimikaade/wonderful:devops-stage-two` |
| `GREEN_IMAGE`      | Docker image for Green pool       | `yimikaade/wonderful:devops-stage-two` |
| `RELEASE_ID_BLUE`  | Release identifier for Blue       | `blue-v1.0.0`                          |
| `RELEASE_ID_GREEN` | Release identifier for Green      | `green-v1.0.0`                         |
| `ACTIVE_POOL`      | Primary routing target            | `blue` or `green`                      |
| `APP_PORT`         | Application port inside container | `3000`                                 |

### Exposed Ports

| Port   | Service   | Purpose                             |
| ------ | --------- | ----------------------------------- |
| `8080` | Nginx     | Public entrypoint (used by clients) |
| `8081` | Blue App  | Direct access + chaos endpoint      |
| `8082` | Green App | Direct access + chaos endpoint      |

### Nginx Failover Configuration

Key settings in `nginx.conf.template`:

```nginx
# Fast failure detection
proxy_connect_timeout 2s;
proxy_send_timeout 3s;
proxy_read_timeout 3s;

# Automatic retry on failures
proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
proxy_next_upstream_timeout 3s;
proxy_next_upstream_tries 2;

# Upstream health monitoring
max_fails=1 fail_timeout=5s;
```

## 📊 Expected Behavior

### Normal State (Blue Active)

- ✅ All requests go to Blue
- ✅ Response headers show `X-App-Pool: blue`
- ✅ 100% success rate (200 OK)

### During Blue Failure

- ✅ Nginx detects failure within 2 seconds
- ✅ Automatically routes to Green (backup)
- ✅ Zero failed client requests (0 non-200s)
- ✅ Response headers now show `X-App-Pool: green`

### After Recovery

- ✅ Blue returns to active pool
- ✅ Green remains available as backup

## 🐛 Troubleshooting

### Issue: Getting 404 errors

```bash
# Check if containers are running
docker-compose ps

# Check Nginx logs
docker-compose logs nginx

# Check app logs
docker-compose logs app_blue
docker-compose logs app_green

# Restart everything
docker-compose down -v
docker-compose up -d
```

### Issue: Headers not showing

```bash
# Use -i flag to see all headers
curl -i http://localhost:8080/version

# Check Nginx is not stripping headers
docker-compose exec nginx cat /etc/nginx/conf.d/default.conf
```

### Issue: Failover not working

```bash
# Verify Green is healthy
curl http://localhost:8082/healthz

# Check Nginx upstream config
docker-compose exec nginx nginx -T | grep upstream -A 5

# Check failover settings
docker-compose exec nginx nginx -T | grep proxy_next_upstream
```

## 🎬 Complete Test Script

Save this as `test_failover.sh`:

```bash
#!/bin/bash

echo "=== Blue/Green Failover Test ==="
echo ""

echo "1. Testing normal state (Blue)..."
BLUE_RESPONSE=$(curl -s -i http://localhost:8080/version | grep "X-App-Pool")
echo "   $BLUE_RESPONSE"

echo ""
echo "2. Triggering chaos on Blue..."
curl -X POST "http://localhost:8081/chaos/start?mode=error"
echo ""

sleep 2

echo ""
echo "3. Testing failover (should be Green)..."
GREEN_RESPONSE=$(curl -s -i http://localhost:8080/version | grep "X-App-Pool")
echo "   $GREEN_RESPONSE"

echo ""
echo "4. Testing stability (10 requests)..."
SUCCESS=0
for i in {1..10}; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/version)
  if [ "$CODE" = "200" ]; then
    ((SUCCESS++))
  fi
  echo "   Request $i: $CODE"
done

echo ""
echo "5. Stopping chaos..."
curl -X POST "http://localhost:8081/chaos/stop"
echo ""

echo ""
echo "=== Results ==="
echo "Success rate: $SUCCESS/10"
if [ $SUCCESS -eq 10 ]; then
  echo "✅ PASS: Zero failed requests during failover"
else
  echo "❌ FAIL: Some requests failed"
fi
```

Run with:

```bash
chmod +x test_failover.sh
./test_failover.sh
```

## 📝 API Endpoints

### Application Endpoints

| Method | Endpoint                    | Description                   | Response                                             |
| ------ | --------------------------- | ----------------------------- | ---------------------------------------------------- |
| GET    | `/version`                  | Get app version and pool info | JSON with headers                                    |
| GET    | `/healthz`                  | Health check                  | `{"status":"OK","message":"Application is running"}` |
| POST   | `/chaos/start?mode=error`   | Start error simulation        | `{"message":"Simulation mode 'error' activated"}`    |
| POST   | `/chaos/start?mode=timeout` | Start timeout simulation      | `{"message":"Simulation mode 'timeout' activated"}`  |
| POST   | `/chaos/stop`               | Stop simulation               | `{"message":"Simulation stopped"}`                   |

### Response Headers

All successful responses include:

- `X-App-Pool`: `blue` or `green` (which pool served the request)
- `X-Release-Id`: Release identifier from environment variable

## 🎓 Implementation Notes

### Why This Design?

1. **Upstream backup directive**: Ensures Green only serves when Blue fails
2. **Tight timeouts**: 2-3 second timeouts detect failures quickly
3. **proxy_next_upstream**: Automatically retries failed requests to backup
4. **Health checks**: Docker monitors container health before routing
5. **Header forwarding**: Preserves application headers for observability

### Trade-offs

- ⚖️ **Fast failover vs false positives**: 2s timeout is aggressive but catches real failures quickly
- ⚖️ **Simplicity vs flexibility**: Static config prioritizes reliability over dynamic routing
- ⚖️ **Resource usage**: Both pools run simultaneously (increased cost, zero downtime)

## 🔒 Production Considerations

For production deployment, consider:

- [ ] Add TLS/HTTPS configuration
- [ ] Implement proper logging and monitoring
- [ ] Add authentication for chaos endpoints
- [ ] Use health check intervals aligned with SLA requirements
- [ ] Configure log rotation for Nginx
- [ ] Add resource limits to containers
- [ ] Implement gradual traffic shifting (canary deployments)
- [ ] Set up alerting for failover events

## 📚 References

- [Nginx Upstream Documentation](http://nginx.org/en/docs/http/ngx_http_upstream_module.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Blue-Green Deployment Pattern](https://martinfowler.com/bliki/BlueGreenDeployment.html)

## 📄 License

MIT

## 👥 Author

Oghenekparobo Stephen - HNG Internship Stage 2 DevOps Task

---
