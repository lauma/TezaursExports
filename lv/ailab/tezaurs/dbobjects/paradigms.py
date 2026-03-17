from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbobjects.gram import Flags


class Paradigm:
    def __init__(self, db_id, paradigm_name, flags):
        self.dbId : int = db_id
        self.name : str = paradigm_name
        self.flags : Flags = flags

    @staticmethod
    def fetch_all_paradigms(connection : DbConnection) -> dict[str, Paradigm]:
        result = {}
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_paradigms = f"""
    SELECT id, data as flags, human_key as paradigm
    FROM {db_connection_info['schema']}.paradigms
    ORDER BY human_key ASC
    """
        cursor.execute(sql_paradigms)
        paradigm_data = cursor.fetchall()
        for p in paradigm_data:
            result[p.paradigm] = Paradigm(p.id, p.paradigm, p.flags)
        return result