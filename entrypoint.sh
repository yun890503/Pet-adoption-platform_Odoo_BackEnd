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
