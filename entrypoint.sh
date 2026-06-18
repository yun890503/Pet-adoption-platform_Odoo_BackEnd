#!/bin/sh
set -e

: "${PORT:=8069}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"
: "${DB_USER:=odoo}"
: "${DB_PASSWORD:=odoo}"
: "${DB_NAME:=Pet-adoption-platform}"
: "${ODOO_ADMIN_PASSWORD:=admin}"

exec python /app/odoo-bin \
  -c /app/odoo-zeabur.conf \
  --http-port="${PORT}" \
  --db_host="${DB_HOST}" \
  --db_port="${DB_PORT}" \
  --db_user="${DB_USER}" \
  --db_password="${DB_PASSWORD}" \
  --admin-passwd="${ODOO_ADMIN_PASSWORD}" \
  -d "${DB_NAME}" \
  --without-demo=all
