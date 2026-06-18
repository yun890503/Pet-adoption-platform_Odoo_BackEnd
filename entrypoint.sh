#!/bin/sh
set -e

: "${PORT:=8080}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"
: "${DB_USER:=odoo}"
: "${DB_PASSWORD:=odoo}"
: "${DB_NAME:=Pet-adoption-platform}"
: "${ODOO_ADMIN_PASSWORD:=admin}"
: "${ODOO_INIT_MODULES:=base,warm_paws_adoption}"
: "${LINE_LIFF_ID:=2010432240-mRjM2C9g}"
: "${LINE_CHANNEL_ID:=2010432240}"
: "${LINE_MESSAGING_CHANNEL_ID:=2010436798}"
: "${LINE_CHANNEL_SECRET:=be9e79d6c28536c84ba61475934b92af}"
: "${LINE_CHANNEL_ACCESS_TOKEN:=}"
: "${FRONTEND_URL:=https://adoption-platform.zeabur.app}"

CONFIG_FILE="/tmp/odoo-zeabur.conf"
cp /app/odoo-zeabur.conf "${CONFIG_FILE}"
sed -i "s/^admin_passwd = .*/admin_passwd = ${ODOO_ADMIN_PASSWORD}/" "${CONFIG_FILE}"

INIT_ARGS=""
export PGPASSWORD="${DB_PASSWORD}"
if command -v psql >/dev/null 2>&1; then
  DB_INITIALIZED="$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT to_regclass('public.ir_module_module') IS NOT NULL;" 2>/dev/null || echo "f")"
  if [ "${DB_INITIALIZED}" != "t" ]; then
    INIT_ARGS="-i ${ODOO_INIT_MODULES}"
  fi
else
  INIT_ARGS="-i ${ODOO_INIT_MODULES}"
fi

if [ -n "${LINE_CHANNEL_ACCESS_TOKEN}" ] && command -v psql >/dev/null 2>&1; then
  psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1 <<SQL || true
INSERT INTO ir_config_parameter (key, value) VALUES ('warm_paws.line_liff_id', '${LINE_LIFF_ID}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
INSERT INTO ir_config_parameter (key, value) VALUES ('warm_paws.line_channel_id', '${LINE_CHANNEL_ID}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
INSERT INTO ir_config_parameter (key, value) VALUES ('warm_paws.line_messaging_channel_id', '${LINE_MESSAGING_CHANNEL_ID}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
INSERT INTO ir_config_parameter (key, value) VALUES ('warm_paws.line_channel_secret', '${LINE_CHANNEL_SECRET}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
INSERT INTO ir_config_parameter (key, value) VALUES ('warm_paws.line_channel_access_token', '${LINE_CHANNEL_ACCESS_TOKEN}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
INSERT INTO ir_config_parameter (key, value) VALUES ('warm_paws.frontend_url', '${FRONTEND_URL}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
SQL
fi

exec python /app/odoo-bin \
  -c "${CONFIG_FILE}" \
  --http-port="${PORT}" \
  --db_host="${DB_HOST}" \
  --db_port="${DB_PORT}" \
  --db_user="${DB_USER}" \
  --db_password="${DB_PASSWORD}" \
  -d "${DB_NAME}" \
  ${INIT_ARGS} \
  --without-demo=all
