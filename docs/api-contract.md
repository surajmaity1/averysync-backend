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

