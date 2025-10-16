# backend-api-django


### To run in dev:

```
pyenv install 3.13.4
python -m pip install virtualenv
python -m virtualenv venv
source venv/Scripts/activate
python -m pip install -r requirements.txt
```



```
python manage.py runserver
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
