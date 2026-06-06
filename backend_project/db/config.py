import logging
from sqlalchemy import create_engine, URL, text
from django.conf import settings


logger = logging.getLogger(__name__)


class DBManager:
    __instance = None

    def __new__(cls, *args, **kwards):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls, *args, **kwards)
            cls.__instance._db = None
            cls.__instance._db_client = None
        return cls.__instance

    def _get_db_client(self):
        if self._db_client is None:
            self._db_client = self.get_new_connection()
        return self._db_client

    def check_db_health(self):
        try:
            db_client = self._get_db_client()
            db_client.execute(text("select 'hello world'"))
            return True
        except Exception as e:
            logger.error(f"Failed: DB connection: {e}")
            return False

    def get_new_connection(self):
        try:
            url_object = URL.create(
                "postgresql+psycopg",
                username=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
            )
            engine = create_engine(url_object)
            connection = engine.connect()
            logger.info("Success: DB connected")
        except Exception as error:
            logger.error(f"Failed: DB connection: {error}")
            connection.close()

        return connection

    def get_db(self):
        if self._db is None:
            self._db = self._get_db_client()[settings.DB_NAME]
        return self._db

    def get_collection(self, colection_name):
        db = self.get_db()
        return db[colection_name]
