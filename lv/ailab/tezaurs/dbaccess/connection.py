import psycopg2
from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo


type DbConnection = psycopg2._psycopg.connection
type JsonData = dict[str,JsonData|list[JsonData|str]]


def db_connect() -> DbConnection:
    if not DbConnectionInfo.host:
        print("Postgres connection error: connection information must be supplied in db_config")
        raise Exception("Postgres connection error: connection information must be supplied in <conn_info>")

    print(f'Connecting to database {DbConnectionInfo.dbname}, schema {DbConnectionInfo.schema}')
    db_connection = psycopg2.connect(
            host=DbConnectionInfo.host,
            port=DbConnectionInfo.port,
            dbname=DbConnectionInfo.dbname,
            user=DbConnectionInfo.user,
            password=DbConnectionInfo.password,
            options=f'-c search_path={DbConnectionInfo.schema}',
        )
    return db_connection


def get_dict_version(connection: DbConnection) -> dict[str, str]:
    cursor = connection.cursor(cursor_factory=DictCursor)
    sql_dict_properties = f"""
    SELECT title, extract(YEAR from release_timestamp) as year, extract(MONTH from release_timestamp) as month,
        info->'dictionary' #>> '{{}}' as dictionary, info->'tag' #>> '{{}}' as tag,
        info->'counts'->'entries' #>> '{{}}' as entries,
        info->'counts'->'lexemes' #>> '{{}}' as lexemes,
        info->'counts'->'senses' #>> '{{}}' as senses,
        info->'title_short' #>> '{{}}' as title_short,
        info->'title_en' #>> '{{}}' as title_long,
        info->'release_name_en' #>> '{{}}' as release_name_en,
        info->'editors_en' #>> '{{}}' as editors_en,
        info->'copyright_en' #>> '{{}}' as copyright_en,
        info->'canonical_url' #>> '{{}}' as url
    FROM {DbConnectionInfo.schema}.metadata
"""
    cursor.execute(sql_dict_properties)
    db_row = cursor.fetchone()
    return {
        'dictionary': db_row['dictionary'],
        'title_short': db_row['title_short'],
        'title_long': db_row['title_long'],
        'tag': db_row['tag'],
        'release_name_en': db_row['release_name_en'],
        'editors_en': db_row['editors_en'],
        'copyright_en': db_row['copyright_en'],
        'entries': db_row['entries'],
        'lexemes': db_row['lexemes'],
        'senses': db_row['senses'],
        'year': db_row['year'],
        'month': db_row['month'],
        'url': db_row['url']}


#from typing import NamedTuple
#from psycopg2.extras import NamedTupleCursor
#def query(sql, parameters, db_connection : DbConnection) -> list[NamedTuple]:
#    cursor = db_connection.cursor(cursor_factory=NamedTupleCursor)
#    cursor.execute(sql, parameters)
#    r = cursor.fetchall()
#    cursor.close()
#    return r
