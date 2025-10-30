#!/usr/bin/env python3
import sys
import os
import re
import time
import io  # <-- ADD THIS LINE
import requests
from collections import deque

# Immediate flush for debugging
print("=== LOG WATCHER STARTING ===", flush=True)

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ACTIVE_POOL = os.getenv('ACTIVE_POOL', 'blue')
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', 2)) / 100
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', 200))
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', 300))

print(f"Config: Pool={ACTIVE_POOL}, Threshold={ERROR_RATE_THRESHOLD*100}%, Window={WINDOW_SIZE}, Cooldown={ALERT_COOLDOWN_SEC}s", flush=True)
print(f"Slack URL: {'CONFIGURED' if SLACK_WEBHOOK_URL else 'MISSING'}", flush=True)

last_seen_pool = ACTIVE_POOL
window = deque(maxlen=WINDOW_SIZE)
last_alert_time = {}
log_file = '/var/log/nginx/access_file.log'


# Reduced skip to see logs faster
SKIP_ON_STARTUP = 10

def parse_log_line(line):
    """
    Parse nginx log line for pool and upstream status.
    Example log format:
    pool="blue" release="blue-v1.0.0" upstream="172.18.0.2:3000" upstream_status=200 ...
    """
    # Try to extract pool - handle both quoted and empty cases
    pool_match = re.search(r'pool="(\w+)"', line)
    served_pool = pool_match.group(1) if pool_match else None
    
    # Extract upstream_status - it comes after upstream_status=
    status_match = re.search(r'upstream_status=(\d+)', line)
    status = int(status_match.group(1)) if status_match else None
    
    # If pool is empty or dash, try to infer from upstream IP
    if not served_pool or served_pool == '-':
        # Check if we can determine from context
        if 'app_blue' in line or '.2:' in line:
            served_pool = 'blue'
        elif 'app_green' in line or '.3:' in line:
            served_pool = 'green'
    
    if served_pool and status:
        is_5xx = status >= 500
        print(f"✓ Parsed: pool={served_pool}, status={status}, is_5xx={is_5xx}", flush=True)
        return served_pool, is_5xx
    else:
        print(f"✗ Parse failed: pool={served_pool}, status={status} | Line: {line[:120]}", flush=True)
        return None, False

def send_slack_alert(title, text):
    """Send alert to Slack with retry logic"""
    if not SLACK_WEBHOOK_URL:
        print(f"⚠️  [NO WEBHOOK] {title}: {text}", flush=True)
        return False
    
    payload = {
        "text": f"🚨 *{title}*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ SLACK SENT: {title}", flush=True)
            return True
        else:
            print(f"❌ SLACK FAILED: Status {response.status_code}, Response: {response.text[:200]}", flush=True)
            return False
    except Exception as e:
        print(f"❌ Slack error: {e}", flush=True)
        return False

def can_alert(alert_type):
    """Check if enough time has passed since last alert of this type"""
    now = time.time()
    last = last_alert_time.get(alert_type, 0)
    cooldown_remaining = ALERT_COOLDOWN_SEC - (now - last)
    
    if cooldown_remaining > 0:
        print(f"⏳ Alert '{alert_type}' on cooldown: {cooldown_remaining:.0f}s remaining", flush=True)
        return False
    
    last_alert_time[alert_type] = now
    return True

print(f"🔍 Waiting for log file: {log_file}", flush=True)

# Wait for log file
while not os.path.exists(log_file):
    print("⏳ Log file not found, waiting...", flush=True)
    time.sleep(2)

print("📖 Log file found! Starting to tail...", flush=True)

processed_lines = 0
consecutive_parse_failures = 0

try:
    with open(log_file, 'r') as f:
        # Check if file is seekable (regular file vs pipe/fifo)
        try:
            f.seek(0, 2)
            print("✅ File is seekable - tailing from end", flush=True)
        except (OSError, io.UnsupportedOperation):
            print("⚠️  File is not seekable (pipe/fifo) - reading from current position", flush=True)
            # For pipes, just start reading from wherever we are
            pass
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue

            processed_lines += 1
            
            # Skip initial logs if configured
            if processed_lines <= SKIP_ON_STARTUP:
                if processed_lines == 1:
                    print(f"⏭️  Skipping first {SKIP_ON_STARTUP} lines...", flush=True)
                continue

            line = line.strip()
            if not line:
                continue

            # Parse the log line
            served_pool, is_5xx = parse_log_line(line)
            
            if served_pool:
                consecutive_parse_failures = 0
                window.append((served_pool, is_5xx))
                
                # FAILOVER DETECTION
                if served_pool != last_seen_pool:
                    print(f"🔄 Pool change detected: {last_seen_pool} → {served_pool}", flush=True)
                    if can_alert('failover'):
                        msg = (f"Traffic has shifted from *{last_seen_pool.upper()}* to *{served_pool.upper()}*\n\n"
                               f"📊 Window size: {len(window)} requests\n"
                               f"⚠️ Please investigate the {last_seen_pool.upper()} pool health.")
                        send_slack_alert("🔄 Failover Detected", msg)
                    last_seen_pool = served_pool
                
                # ERROR RATE DETECTION
                if len(window) >= WINDOW_SIZE:
                    error_count = sum(1 for _, err in window if err)
                    error_rate = (error_count / len(window)) * 100
                    
                    if error_count > 0:  # Only log when there are errors
                        print(f"📊 Error rate: {error_rate:.1f}% ({error_count}/{len(window)}) on {served_pool}", flush=True)
                    
                    if error_rate > ERROR_RATE_THRESHOLD * 100:
                        if can_alert('error_rate'):
                            msg = (f"High error rate detected: *{error_rate:.1f}%* 5xx errors\n\n"
                                   f"📈 {error_count} errors in last {len(window)} requests\n"
                                   f"🎯 Current pool: *{served_pool.upper()}*\n"
                                   f"⚠️ Threshold: {ERROR_RATE_THRESHOLD * 100}%")
                            send_slack_alert("⚠️ High Error Rate Alert", msg)
            else:
                consecutive_parse_failures += 1
                if consecutive_parse_failures >= 10:
                    print(f"⚠️  Warning: {consecutive_parse_failures} consecutive parse failures", flush=True)
                    consecutive_parse_failures = 0  # Reset counter

except KeyboardInterrupt:
    print("\n👋 Watcher stopped by user", flush=True)
except Exception as e:
    print(f"💥 CRITICAL ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
    # Keep container running for debugging
    while True:
        time.sleep(60)