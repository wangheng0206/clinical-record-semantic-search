#!/bin/bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	CREATE EXTENSION IF NOT EXISTS vector;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-SQL
	CREATE DATABASE clinical_search_test OWNER $POSTGRES_USER;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname clinical_search_test <<-SQL
	CREATE EXTENSION IF NOT EXISTS vector;
SQL
