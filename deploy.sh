<<<<<<< HEAD
#!/usr/bin/env bash
# ==============================================================
# Kaizen Production Deployment Script
# Target: app.kaizenx.in on AWS EC2 (single instance)
# ==============================================================
set -euo pipefail

DOMAIN="app.kaizenx.in"
EMAIL="${CERTBOT_EMAIL:-admin@kaizenx.in}"
COMPOSE="docker compose"

echo "=========================================="
echo " Kaizen Deployment — $DOMAIN"
echo "=========================================="

# ------------------------------------------------------------------
# PRE-FLIGHT CHECKS
# ------------------------------------------------------------------
echo ""
echo "[1/8] Pre-flight checks..."

# Ensure .env exists
if [ ! -f .env ]; then
  echo "ERROR: .env file not found."
  echo "  Copy .env.production to .env and fill in real secrets:"
  echo "    cp .env.production .env"
  echo "    nano .env"
  exit 1
fi

# Validate critical env vars
source .env
if [ "${SECRET_KEY:-}" = "" ] || [[ "${SECRET_KEY}" == *"CHANGE_ME"* ]]; then
  echo "ERROR: SECRET_KEY is not set or still contains CHANGE_ME."
  echo "  Generate one with:"
  echo "    python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
  exit 1
fi
if [[ "${POSTGRES_PASSWORD:-changeme}" == *"CHANGE_ME"* ]] || [ "${POSTGRES_PASSWORD:-}" = "changeme" ]; then
  echo "ERROR: POSTGRES_PASSWORD is not set to a real password."
  exit 1
fi
if [[ "${INTERNAL_SECRET:-change_this}" == *"CHANGE_ME"* ]] || [ "${INTERNAL_SECRET:-}" = "change_this" ]; then
  echo "ERROR: INTERNAL_SECRET is not set to a real token."
  exit 1
fi

echo "  .env validated ✓"

# Check DNS
echo ""
echo "[2/8] Checking DNS for $DOMAIN..."
RESOLVED_IP=$(dig +short "$DOMAIN" 2>/dev/null || true)
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s ifconfig.me 2>/dev/null || true)

if [ -z "$RESOLVED_IP" ]; then
  echo "WARNING: Could not resolve $DOMAIN. Ensure DNS A record points to this server."
  echo "  Expected IP: $PUBLIC_IP"
  echo "  Continuing anyway (DNS may be propagating)..."
else
  echo "  $DOMAIN → $RESOLVED_IP"
  if [ "$RESOLVED_IP" = "$PUBLIC_IP" ]; then
    echo "  Matches server IP ✓"
  else
    echo "  WARNING: DNS resolves to $RESOLVED_IP but server IP is $PUBLIC_IP"
    echo "  SSL certificate generation may fail if DNS is wrong."
  fi
fi

# ------------------------------------------------------------------
# SSL CERTIFICATE SETUP
# ------------------------------------------------------------------
echo ""
echo "[3/8] Setting up SSL certificates..."

CERT_DIR="./certbot/conf/live/$DOMAIN"
CERTBOT_WWW="./certbot/www"

mkdir -p "$CERTBOT_WWW"
mkdir -p "./certbot/conf"

if [ -f "$CERT_DIR/fullchain.pem" ]; then
  echo "  SSL certificates already exist ✓"
  echo "  To renew: certbot renew --webroot -w $CERTBOT_WWW"
else
  echo "  No SSL certificates found. Generating temporary self-signed cert..."
  echo "  (Will be replaced with Let's Encrypt after nginx starts)"

  # Create directory structure that certbot expects
  mkdir -p "$CERT_DIR"

  # Generate self-signed certificate (temporary — allows nginx to start)
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -subj "/CN=$DOMAIN" \
    2>/dev/null

  echo "  Temporary self-signed cert created ✓"
fi

# ------------------------------------------------------------------
# BUILD & START CONTAINERS
# ------------------------------------------------------------------
echo ""
echo "[4/8] Building containers..."
$COMPOSE build --no-cache

echo ""
echo "[5/8] Starting services..."
$COMPOSE up -d

echo ""
echo "  Waiting for services to stabilize (15s)..."
sleep 15

# Check container health
echo ""
echo "[6/8] Checking container status..."
$COMPOSE ps

# Quick health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/healthz/" 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "200" ]; then
  echo "  nginx is responding ✓"
else
  echo "  WARNING: nginx returned HTTP $HTTP_STATUS"
  echo "  Check logs: $COMPOSE logs nginx"
fi

# ------------------------------------------------------------------
# OBTAIN REAL SSL CERTIFICATE
# ------------------------------------------------------------------
echo ""
echo "[7/8] Obtaining Let's Encrypt certificate..."

if [ -f "$CERT_DIR/fullchain.pem" ] && openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -issuer 2>/dev/null | grep -qi "let's encrypt"; then
  echo "  Valid Let's Encrypt cert already installed ✓"
else
  echo "  Running certbot..."
  # Stop nginx temporarily so certbot can bind port 80, OR use webroot mode
  # Webroot mode is preferred (no downtime)
  docker run --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot certonly \
      --webroot \
      -w /var/www/certbot \
      -d "$DOMAIN" \
      --email "$EMAIL" \
      --agree-tos \
      --no-eff-email \
      --force-renewal

  if [ $? -eq 0 ]; then
    echo "  Let's Encrypt certificate obtained ✓"
    echo "  Reloading nginx with real certificate..."
    $COMPOSE restart nginx
    sleep 5
  else
    echo "  WARNING: certbot failed. Site will use self-signed cert."
    echo "  You can retry manually:"
    echo "    docker run --rm -v \$(pwd)/certbot/conf:/etc/letsencrypt -v \$(pwd)/certbot/www:/var/www/certbot certbot/certbot certonly --webroot -w /var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos --no-eff-email"
  fi
fi

# ------------------------------------------------------------------
# FINAL VALIDATION
# ------------------------------------------------------------------
echo ""
echo "[8/8] Final validation..."
echo ""

PASS=0
FAIL=0

# Test HTTPS
HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/" 2>/dev/null || echo "000")
if [ "$HTTPS_STATUS" = "200" ]; then
  echo "  ✅ HTTPS $DOMAIN → $HTTPS_STATUS (frontend loads)"
  PASS=$((PASS+1))
else
  echo "  ❌ HTTPS $DOMAIN → $HTTPS_STATUS"
  FAIL=$((FAIL+1))
fi

# Test HTTP redirect
HTTP_REDIR=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN/" 2>/dev/null || echo "000")
if [ "$HTTP_REDIR" = "301" ]; then
  echo "  ✅ HTTP → HTTPS redirect working ($HTTP_REDIR)"
  PASS=$((PASS+1))
else
  echo "  ❌ HTTP redirect returned $HTTP_REDIR (expected 301)"
  FAIL=$((FAIL+1))
fi

# Test API health
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/healthz/" 2>/dev/null || echo "000")
if [ "$API_STATUS" = "200" ]; then
  echo "  ✅ API health check → $API_STATUS"
  PASS=$((PASS+1))
else
  echo "  ❌ API health check → $API_STATUS"
  FAIL=$((FAIL+1))
fi

# Test API auth endpoint
CSRF_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/api/auth/csrf/" 2>/dev/null || echo "000")
if [ "$CSRF_STATUS" = "200" ]; then
  echo "  ✅ CSRF endpoint → $CSRF_STATUS"
  PASS=$((PASS+1))
else
  echo "  ❌ CSRF endpoint → $CSRF_STATUS"
  FAIL=$((FAIL+1))
fi

# Test that service_b is NOT publicly accessible
SB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN:8000/health" 2>/dev/null || echo "000")
if [ "$SB_STATUS" = "000" ]; then
  echo "  ✅ Service B is NOT publicly accessible"
  PASS=$((PASS+1))
else
  echo "  ❌ Service B responded on port 8000 (should be blocked)"
  FAIL=$((FAIL+1))
fi

# Check for localhost references in frontend
LOCALHOST_REFS=$(curl -s "https://$DOMAIN/" 2>/dev/null | grep -c "localhost" || true)
if [ "$LOCALHOST_REFS" = "0" ]; then
  echo "  ✅ No localhost references in frontend HTML"
  PASS=$((PASS+1))
else
  echo "  ❌ Found $LOCALHOST_REFS localhost references in frontend"
  FAIL=$((FAIL+1))
fi

echo ""
echo "=========================================="
echo " Results: $PASS passed, $FAIL failed"
echo "=========================================="

if [ "$FAIL" -eq 0 ]; then
  echo ""
  echo " 🟢 VERDICT: READY"
  echo ""
  echo " app.kaizenx.in is live and operational."
  echo ""
else
  echo ""
  echo " 🟡 VERDICT: READY WITH WARNINGS"
  echo ""
  echo " Check failed items above. Common fixes:"
  echo "   Logs:  $COMPOSE logs -f"
  echo "   nginx: $COMPOSE logs nginx"
  echo "   Django: $COMPOSE logs service_a"
  echo "   FastAPI: $COMPOSE logs service_b"
  echo ""
fi

echo " Useful commands:"
echo "   Logs:         $COMPOSE logs -f"
echo "   Restart:      $COMPOSE restart"
echo "   Rebuild:      $COMPOSE build --no-cache && $COMPOSE up -d"
echo "   SSL renew:    docker run --rm -v \$(pwd)/certbot/conf:/etc/letsencrypt -v \$(pwd)/certbot/www:/var/www/certbot certbot/certbot renew"
echo "   SSL cron:     0 3 * * 0 cd $(pwd) && docker run --rm -v \$(pwd)/certbot/conf:/etc/letsencrypt -v \$(pwd)/certbot/www:/var/www/certbot certbot/certbot renew && $COMPOSE restart nginx"
echo ""
=======
#!/bin/bash
set -e

echo "Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main

echo "Stopping containers..."
docker-compose down

echo "Building and starting containers..."
docker-compose up --build -d

echo "Deployment finished!"
docker ps
>>>>>>> bf6d9b2864724c9e7c20b4555310c1ba3ad2014e
