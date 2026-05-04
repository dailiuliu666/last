from pathlib import Path
from dotenv import dotenv_values
import pymysql

config = dotenv_values(Path(r'D:\My_Project\last\graduation_finance_platform\.env'))
host = config.get('MYSQL_HOST', '127.0.0.1')
port = int(config.get('MYSQL_PORT', '3306'))
user = config.get('MYSQL_USER', 'root')
password = config.get('MYSQL_PASSWORD', '')
database = config.get('MYSQL_DB', 'graduation_finance')
charset = config.get('MYSQL_CHARSET', 'utf8mb4')

conn = pymysql.connect(host=host, port=port, user=user, password=password, charset=charset, autocommit=True)
try:
    with conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` DEFAULT CHARACTER SET {charset}")
        print(f"database_ready:{database}")
finally:
    conn.close()

from app.core.database import Base, engine
import app.models  # noqa: F401

Base.metadata.create_all(bind=engine)
print('tables_ready')
