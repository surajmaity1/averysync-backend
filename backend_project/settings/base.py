import os

DEBUG = True

# Postgres Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "backend_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "todo_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "todo_postgres")