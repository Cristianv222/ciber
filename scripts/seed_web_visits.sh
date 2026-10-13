#!/usr/bin/env bash
# Siembra visitas web de demo (dominios reales) para ver la página "Navegación".
# En producción esto lo llena solo el ingestor (SNI/DNS/HTTP). Datos de prueba.
#
# Uso:  ./scripts/seed_web_visits.sh [API_BASE_URL]
set -euo pipefail
API="${1:-http://localhost:8000}"
EP="$API/api/web-visits/"

# dominio | fuente | repeticiones
ROWS=(
  "www.google.com|tls|40" "www.youtube.com|tls|35" "www.facebook.com|tls|22"
  "www.instagram.com|tls|28" "web.whatsapp.com|tls|18" "www.tiktok.com|tls|25"
  "www.netflix.com|tls|12" "github.com|tls|16" "stackoverflow.com|tls|9"
  "www.microsoft.com|tls|7" "es.wikipedia.org|tls|11" "www.amazon.com|tls|8"
  "chatgpt.com|tls|20" "x.com|tls|14" "www.reddit.com|tls|6"
  "mail.google.com|dns|15" "cdn.jsdelivr.net|dns|10" "fonts.gstatic.com|dns|9"
)
CLIENTS=("10.0.0.21" "10.0.0.22" "10.0.0.35" "192.168.1.50" "192.168.1.77")

post() { # domain source client path method
  curl -sf -o /dev/null -X POST "$EP" -H 'Content-Type: application/json' -d "$(cat <<JSON
{"src_ip":"$3","dst_ip":"142.250.0.$((RANDOM%250))","dst_port":$([ "$2" = dns ] && echo 53 || echo 443),
 "source":"$2","domain":"$1","url_path":${4:-null},"method":${5:-null}}
JSON
)"; }

count=0
for row in "${ROWS[@]}"; do
  IFS='|' read -r domain source reps <<< "$row"
  for ((i=0;i<reps;i++)); do
    c="${CLIENTS[$((RANDOM%${#CLIENTS[@]}))]}"
    post "$domain" "$source" "$c" && count=$((count+1)) || true
  done
  echo "  $domain ($source): $reps"
done

# Algunas visitas HTTP en claro (con ruta), como las vería un firewall
post "ejemplo-intranet.local" "http" "10.0.0.21" '"/login"' '"POST"' && count=$((count+1)) || true
post "ejemplo-intranet.local" "http" "10.0.0.22" '"/dashboard"' '"GET"' && count=$((count+1)) || true
post "testphp.vulnweb.com" "http" "10.0.0.35" '"/search.php?q=admin"' '"GET"' && count=$((count+1)) || true

echo "Total sembrado: $count visitas web"
