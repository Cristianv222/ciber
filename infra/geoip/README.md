# infra/geoip — Base de datos GeoIP (offline)

Geolocaliza las IPs atacantes **sin enviar nada a servicios externos** (encaja con
la restricción de que los datos no salen de la universidad).

Se usa **DB-IP City Lite** (gratuita, licencia CC-BY). El archivo `.mmdb` NO se versiona
(es grande, ~120 MB). Descárgalo así:

```bash
mkdir -p infra/geoip && cd infra/geoip
MONTH=$(date +%Y-%m)
curl -fSL -o db.mmdb.gz "https://download.db-ip.com/free/dbip-city-lite-$MONTH.mmdb.gz"
gunzip -f db.mmdb.gz && mv db.mmdb dbip-city-lite.mmdb
```

El backend lo monta en `/geoip/dbip-city-lite.mmdb` (variable `GEOIP_DB`).
Atribución requerida por la licencia: "IP Geolocation by DB-IP" (https://db-ip.com).
