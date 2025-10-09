import logging
import psycopg as Database

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
            curser = db_client.cursor()
            curser.execute("SELECT 1;")
            return True
        except Exception as e:
            logger.error(f'Failed: DB connection: {e}')
            return False


    def get_new_connection(self):
        try:
            conn_params = {
                "dbname": settings.POSTGRES_DB,
                "user": settings.POSTGRES_USER,
                "password": settings.POSTGRES_PASSWORD,
                "host": settings.POSTGRES_HOST,
                "port": settings.POSTGRES_PORT,
            }
            connection = Database.connect(**conn_params)
            logger.info('Success: DB connected')
        except Exception as error:
            logger.error(f'Failed: DB connection: {error}')
            connection.close()
            
        return connection