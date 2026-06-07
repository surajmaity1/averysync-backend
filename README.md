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

### APIs:

Health API: 
```bash
http://localhost:8000/v1/health
```

GOOGLE LogIn API: 
```bash
http://localhost:8000/v1/auth/google/login
```

Users API: 
```bash
http://localhost:8000/v1/users?profile=true
```

Posts API: 
```bash
http://localhost:8000/v1/posts
```