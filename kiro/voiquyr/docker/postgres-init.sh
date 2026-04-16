#!/bin/bash
# Creates additional databases on first postgres startup.
# The primary database (euvoice) is already created by POSTGRES_DB.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE voiquyr_cc'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'voiquyr_cc')\gexec
EOSQL
