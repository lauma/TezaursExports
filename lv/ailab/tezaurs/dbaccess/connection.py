import psycopg2

from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info

type DbConnection = psycopg2._psycopg.connection

def db_connect() -> DbConnection:
    if db_connection_info is None or db_connection_info["host"] is None or len(db_connection_info["host"]) == 0:
        print("Postgres connection error: connection information must be supplied in db_config")
        raise Exception("Postgres connection error: connection information must be supplied in <conn_info>")

    print(f'Connecting to database {db_connection_info["dbname"]}, schema {db_connection_info["schema"]}')
    db_connection = psycopg2.connect(
            host=db_connection_info['host'],
            port=db_connection_info['port'],
            dbname=db_connection_info['dbname'],
            user=db_connection_info['user'],
            password=db_connection_info['password'],
            options=f'-c search_path={db_connection_info["schema"]}',
        )
    return db_connection

#from typing import NamedTuple
#from psycopg2.extras import NamedTupleCursor
#def query(sql, parameters, db_connection : DbConnection) -> list[NamedTuple]:
#    cursor = db_connection.cursor(cursor_factory=NamedTupleCursor)
#    cursor.execute(sql, parameters)
#    r = cursor.fetchall()
#    cursor.close()
#    return r
