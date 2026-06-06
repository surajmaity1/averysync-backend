# backend-api-django


### To run in dev:

```bash
pyenv install 3.13.4
python -m pip install virtualenv
python -m virtualenv venv
source venv/Scripts/activate
python -m pip install -r requirements.txt
python manage.py makemigrations backend
python manage.py migrate
python manage.py runserver
python3 manage.py test --verbosity 2
```

### GENERATE PRIVATE & PUBLIC KEY:
```
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

### Create DB Table and Schema and change the schema:
```
CREATE DATABASE backend_db
\c backend_db
show search_path
set search_path to backend_db, public
ALTER ROLE postgres_user_name set SEARCH_PATH = backend_db
DROP DATABASE backend_db WITH (FORCE);
```

APIs:

Health API: 
```
http://localhost:8000/v1/health
```

GOOGLE LogIn API: 
```
http://localhost:8000/v1/auth/google/login
```

Users API: 
```
http://localhost:8000/v1/users?profile=true
```

Posts API: 
```
http://localhost:8000/v1/posts
```