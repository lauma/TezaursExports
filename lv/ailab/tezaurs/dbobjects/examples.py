from typing import Optional
from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo


class Example:
    def __init__(self, db_id : int, text : str, hidden : bool,
                 source : Optional[str] = None, token_location : Optional[int] = None):
        self.dbID : int = db_id
        self.text : str = text
        self.hidden : bool = hidden
        self.source : Optional[str] = source
        self.tokenLocation : Optional[int] = token_location

    @staticmethod
    def fetch_examples(connection : DbConnection, parent_id : int,
                       entry_level_samples : bool = False) -> list[Example]:
        if not parent_id:
            return []
        where_clause = "sense_id"
        if entry_level_samples:
            where_clause = 'entry_id'
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_samples = f"""
    SELECT id, content, data->>'CitedSource' as source, (data->>'TokenLocation')::int as location, hidden, reason_for_hiding
    FROM {DbConnectionInfo.schema}.examples
    WHERE {where_clause} = {parent_id} and (NOT hidden or reason_for_hiding='not-public')
    ORDER BY hidden, order_no
    """
        cursor.execute(sql_samples)
        samples = cursor.fetchall()
        if not samples:
            return []
        result = []
        for db_row in samples:
            sample = Example(db_row['id'], db_row['content'], db_row['hidden'],
                             db_row['source'], db_row['location'])
            result.append(sample)
        return result
