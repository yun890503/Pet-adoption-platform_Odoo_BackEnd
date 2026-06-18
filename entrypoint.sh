#!/bin/sh
set -e

: "${PORT:=8080}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"
: "${DB_USER:=odoo}"
: "${DB_PASSWORD:=odoo}"
: "${DB_NAME:=Pet-adoption-platform}"
: "${ODOO_ADMIN_PASSWORD:=admin}"

CONFIG_FILE="/tmp/odoo-zeabur.conf"
cp /app/odoo-zeabur.conf "${CONFIG_FILE}"
sed -i "s/^admin_passwd = .*/admin_passwd = ${ODOO_ADMIN_PASSWORD}/" "${CONFIG_FILE}"

exec python /app/odoo-bin \
  -c "${CONFIG_FILE}" \
  --http-port="${PORT}" \
  --db_host="${DB_HOST}" \
  --db_port="${DB_PORT}" \
  --db_user="${DB_USER}" \
  --db_password="${DB_PASSWORD}" \
  -d "${DB_NAME}" \
  --without-demo=all
