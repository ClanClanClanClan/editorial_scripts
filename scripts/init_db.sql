-- Database initialization for Editorial Command Center
-- This script runs automatically when the container starts

-- Create the application user if it doesn't exist
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'ecc_user') THEN
      CREATE ROLE ecc_user WITH LOGIN PASSWORD 'ecc_password';
   END IF;
END
$do$;

-- Create the database if it doesn't exist
SELECT 'CREATE DATABASE ecc_db OWNER ecc_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ecc_db')\gexec

-- Connect to the ecc_db database to set up schema
\c ecc_db

-- Grant all privileges to ecc_user
GRANT ALL PRIVILEGES ON DATABASE ecc_db TO ecc_user;
GRANT ALL ON SCHEMA public TO ecc_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ecc_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ecc_user;

-- Create the ecc schema if it does not exist
CREATE SCHEMA IF NOT EXISTS ecc;
GRANT ALL ON SCHEMA ecc TO ecc_user;

-- Example table to verify connectivity
CREATE TABLE IF NOT EXISTS ecc.healthcheck (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
