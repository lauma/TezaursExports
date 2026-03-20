from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.gram import Flags


class Paradigm:
    def __init__(self, db_id, paradigm_name, flags):
        self.dbId : int = db_id
        self.name : str = paradigm_name
        self.flags : Flags = {} if flags is None else flags

    @staticmethod
    def fetch_all_paradigms(connection : DbConnection) -> dict[str, Paradigm]:
        result = {}
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_paradigms = f"""
    SELECT id, data as flags, human_key as paradigm
    FROM {DbConnectionInfo.schema}.paradigms
    ORDER BY human_key ASC
    """
        cursor.execute(sql_paradigms)
        paradigms = cursor.fetchall()
        for db_row in paradigms:
            result[db_row['paradigm']] = Paradigm(db_row['id'], db_row['paradigm'], db_row['flags'])
        return result