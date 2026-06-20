#!/bin/sh
set -e

: "${PORT:=8080}"
: "${ODOO_HTTP_PORT:=8069}"
: "${ODOO_GEVENT_PORT:=8072}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"
: "${DB_USER:=odoo}"
: "${DB_PASSWORD:=odoo}"
: "${DB_NAME:=Pet-adoption-platform}"
: "${ODOO_ADMIN_PASSWORD:=admin}"
: "${ODOO_DATA_DIR:=/var/lib/odoo}"
: "${ODOO_INIT_MODULES:=base,warm_paws_adoption}"
: "${ODOO_UPDATE_MODULES:=warm_paws_adoption}"
: "${ODOO_WORKERS:=2}"
: "${ODOO_MAX_CRON_THREADS:=1}"
: "${ODOO_CLEAN_MISSING_FILESTORE:=1}"
: "${ODOO_DISABLE_WEBSOCKET:=1}"
: "${LINE_LIFF_ID:=2010432240-mRjM2C9g}"
: "${LINE_CHANNEL_ID:=2010432240}"
: "${LINE_MESSAGING_CHANNEL_ID:=2010436798}"
: "${LINE_CHANNEL_SECRET:=be9e79d6c28536c84ba61475934b92af}"
: "${LINE_CHANNEL_ACCESS_TOKEN:=}"
: "${FRONTEND_URL:=https://adoption-platform.zeabur.app}"
: "${BACKEND_URL:=https://heartwarming.zeabur.app}"

CONFIG_FILE="/tmp/odoo-zeabur.conf"
cp /app/odoo-zeabur.conf "${CONFIG_FILE}"
sed -i "s/^admin_passwd = .*/admin_passwd = ${ODOO_ADMIN_PASSWORD}/" "${CONFIG_FILE}"
sed -i "s|^data_dir = .*|data_dir = ${ODOO_DATA_DIR}|" "${CONFIG_FILE}"
mkdir -p "${ODOO_DATA_DIR}"

INIT_ARGS=""
UPDATE_ARGS=""
export PGPASSWORD="${DB_PASSWORD}"
if command -v psql >/dev/null 2>&1; then
  DB_INITIALIZED="$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT to_regclass('public.ir_module_module') IS NOT NULL;" 2>/dev/null || echo "f")"
  if [ "${DB_INITIALIZED}" != "t" ]; then
    INIT_ARGS="-i ${ODOO_INIT_MODULES}"
  elif [ -n "${ODOO_UPDATE_MODULES}" ]; then
    UPDATE_ARGS="-u ${ODOO_UPDATE_MODULES}"
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
INSERT INTO ir_config_parameter (key, value) VALUES ('warm_paws.backend_url', '${BACKEND_URL}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
INSERT INTO ir_config_parameter (key, value) VALUES ('web.base.url', '${BACKEND_URL}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
SQL
fi

if command -v psql >/dev/null 2>&1; then
  psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1 <<SQL || true
INSERT INTO ir_config_parameter (key, value) VALUES ('warm_paws.backend_url', '${BACKEND_URL}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
INSERT INTO ir_config_parameter (key, value) VALUES ('web.base.url', '${BACKEND_URL}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
SQL
fi

if [ "${ODOO_CLEAN_MISSING_FILESTORE}" = "1" ] && [ "${DB_INITIALIZED}" = "t" ] && command -v psql >/dev/null 2>&1; then
  MISSING_IDS_FILE="/tmp/odoo-missing-attachments.txt"
  : > "${MISSING_IDS_FILE}"
  psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -At -F '|' \
    -c "SELECT id, store_fname FROM ir_attachment WHERE store_fname IS NOT NULL AND store_fname != '';" 2>/dev/null |
  while IFS='|' read -r ATTACHMENT_ID STORE_FNAME; do
    if [ -n "${ATTACHMENT_ID}" ] && [ -n "${STORE_FNAME}" ] && [ ! -f "${ODOO_DATA_DIR}/filestore/${DB_NAME}/${STORE_FNAME}" ]; then
      printf '%s\n' "${ATTACHMENT_ID}" >> "${MISSING_IDS_FILE}"
    fi
  done
  if [ -s "${MISSING_IDS_FILE}" ]; then
    MISSING_IDS="$(paste -sd, "${MISSING_IDS_FILE}")"
    echo "Removing missing filestore attachment records: ${MISSING_IDS}"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1 <<SQL || true
DELETE FROM ir_attachment WHERE id IN (${MISSING_IDS});
SQL
  fi
fi

ODOO_REALTIME_UPSTREAM="odoo_gevent"
if [ "${ODOO_WORKERS}" = "0" ]; then
  ODOO_REALTIME_UPSTREAM="odoo"
fi
ODOO_REALTIME_DIRECTIVE="proxy_pass http://${ODOO_REALTIME_UPSTREAM};"
if [ "${ODOO_DISABLE_WEBSOCKET}" = "1" ]; then
  ODOO_REALTIME_DIRECTIVE="return 204;"
fi

cat > /tmp/nginx.conf <<EOF
worker_processes auto;
pid /tmp/nginx.pid;

events {
  worker_connections 1024;
}

http {
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
  client_max_body_size 200m;
  proxy_read_timeout 720s;
  proxy_connect_timeout 720s;
  proxy_send_timeout 720s;
  proxy_buffering off;

  upstream odoo {
    server 127.0.0.1:${ODOO_HTTP_PORT};
  }

  upstream odoo_gevent {
    server 127.0.0.1:${ODOO_GEVENT_PORT};
  }

  server {
    listen ${PORT};

    location /websocket {
      ${ODOO_REALTIME_DIRECTIVE}
      proxy_http_version 1.1;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /longpolling {
      ${ODOO_REALTIME_DIRECTIVE}
      proxy_http_version 1.1;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
      proxy_pass http://odoo;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
    }
  }
}
EOF

python /app/odoo-bin \
  -c "${CONFIG_FILE}" \
  --http-port="${ODOO_HTTP_PORT}" \
  --gevent-port="${ODOO_GEVENT_PORT}" \
  --db_host="${DB_HOST}" \
  --db_port="${DB_PORT}" \
  --db_user="${DB_USER}" \
  --db_password="${DB_PASSWORD}" \
  --workers="${ODOO_WORKERS}" \
  --max-cron-threads="${ODOO_MAX_CRON_THREADS}" \
  -d "${DB_NAME}" \
  ${INIT_ARGS} \
  ${UPDATE_ARGS} \
  --without-demo=all &

ODOO_PID="$!"
trap 'kill "${ODOO_PID}" 2>/dev/null || true' INT TERM

wait_for_port() {
  HOST="$1"
  PORT_TO_CHECK="$2"
  LABEL="$3"
  for attempt in $(seq 1 60); do
    if python - "$HOST" "$PORT_TO_CHECK" <<'PY' >/dev/null 2>&1
import socket
import sys

host, port = sys.argv[1], int(sys.argv[2])
with socket.create_connection((host, port), timeout=1):
    pass
PY
    then
      echo "${LABEL} is ready on ${HOST}:${PORT_TO_CHECK}"
      return 0
    fi
    if ! kill -0 "${ODOO_PID}" 2>/dev/null; then
      echo "Odoo exited before ${LABEL} became ready"
      wait "${ODOO_PID}"
      exit 1
    fi
    sleep 1
  done
  echo "${LABEL} did not become ready on ${HOST}:${PORT_TO_CHECK}; starting nginx anyway"
  return 0
}

wait_for_port 127.0.0.1 "${ODOO_HTTP_PORT}" "Odoo HTTP"
if [ "${ODOO_WORKERS}" != "0" ] && [ "${ODOO_DISABLE_WEBSOCKET}" != "1" ]; then
  wait_for_port 127.0.0.1 "${ODOO_GEVENT_PORT}" "Odoo gevent"
fi

exec nginx -c /tmp/nginx.conf -g 'daemon off;'
