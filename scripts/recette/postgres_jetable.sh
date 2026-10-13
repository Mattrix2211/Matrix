#!/bin/bash
# PostgreSQL jetable pour la recette : démarre ou arrête une instance locale (port 54329).
# Usage : postgres_jetable.sh start|stop. Variables à exporter ensuite : voir le message affiché.
set -e
BIN=$(ls -d /usr/lib/postgresql/*/bin | tail -1)
DIR=/var/tmp/pg_recette
PORT=54329
case "$1" in
  start)
    if [ ! -d "$DIR/data" ]; then
      mkdir -p "$DIR" && chown postgres "$DIR"
      su postgres -c "$BIN/initdb -D $DIR/data -A trust >/dev/null"
    fi
    su postgres -c "$BIN/pg_ctl -D $DIR/data -o '-p $PORT -k $DIR' -l $DIR/log -w start" || true
    psql -h "$DIR" -p $PORT -U postgres -tAc "select 1 from pg_roles where rolname='matrix'" | grep -q 1 \
      || psql -h "$DIR" -p $PORT -U postgres -c "create user matrix superuser password 'matrix'"
    echo "export DJANGO_DEBUG=1 DB_HOST=127.0.0.1 DB_PORT=$PORT DB_USER=matrix DB_PASSWORD=matrix DB_NAME=<base_dediee>"
    echo "Créer une base dédiée par agent : psql -h $DIR -p $PORT -U postgres -c 'create database <nom> owner matrix'"
    ;;
  stop)
    su postgres -c "$BIN/pg_ctl -D $DIR/data -m fast stop" && rm -rf "$DIR"
    ;;
  *) echo "usage: $0 start|stop"; exit 1;;
esac
