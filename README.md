# backend-api-django

### To run in dev:

```bash
pyenv install 3.13.4
python -m pip install virtualenv
python -m venv venv # on windows - python -m virtualenv venv
source venv/bin/activate # on windows - source venv/Scripts/activate
python -m pip install -r requirements.txt
python manage.py makemigrations backend
python manage.py migrate
python manage.py runserver
```

### Quick start command after setup

```bash
source venv/Scripts/activate && python manage.py runserver # windows
source venv/bin/activate && python manage.py runserver # linux
```



### To run tests locally:

```bash
python3 manage.py test --verbosity 2

# for individual test (for repository specific test)
python manage.py test <path>
```

### To run workflow locally:

- [Act Docs](https://nektosact.com/usage/index.html)

```bash
act -W '.github/workflows/<yml-file-name.yml>' --container-architecture=linux/amd64
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
