Create schema:
```sql
create schema backend_db;
```

User table:
```sql
CREATE TABLE "users" (
    "id" SERIAL PRIMARY KEY,
    "user_id" VARCHAR(255) NOT NULL UNIQUE,
    "email" VARCHAR(254) NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "image" VARCHAR(500),
    "sign_in_provider" VARCHAR(20) NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE
);
```

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

```
Post table:
```sql

-- Create the table inside the backend_db schema
CREATE TABLE backend_db.posts (
    id UUID PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description VARCHAR(300) DEFAULT NULL,
    type VARCHAR(10) DEFAULT 'POST',
    is_recorded BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    created_by VARCHAR(100) NOT NULL,
    updated_by VARCHAR(100) DEFAULT NULL
);

-- Create indexes in the same schema
CREATE INDEX posts_created_at_idx ON backend_db.posts (created_at);
CREATE INDEX posts_type_idx ON backend_db.posts (type);
```

Reminders table:
```sql

```

```sql
```