from typing import Optional
from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo


class DictSource:
    def __init__(self, abbreviation : str, title : str, url : Optional[str] = None,
                 details : Optional[str] = None):
        self.abbreviation : str = abbreviation
        self.title : str = title
        self.details : Optional[str] = details
        self.url : Optional[str] = url


    @staticmethod
    def fetch_all_sources(connection : DbConnection) -> list[DictSource]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_dict_sources = f"""
            SELECT abbr, title, url
            FROM {DbConnectionInfo.schema}.sources
            ORDER BY abbr ASC
        """
        cursor.execute(sql_dict_sources)
        sources = cursor.fetchall()
        if not sources:
            return []
        result = []
        for row in sources:
            result.append(DictSource(row['abbr'], row['title'], row['url']))
        return result


    @staticmethod
    def fetch_sources_by_esl_id(connection : DbConnection, entry_id : Optional[int] = None,
                                lexeme_id : Optional[int] = None, sense_id : Optional[int] = None) -> list[DictSource]:
        if not entry_id and not sense_id and not lexeme_id:
            return []
        cursor = connection.cursor(cursor_factory=DictCursor)
        where_clause = ""
        if entry_id:
            where_clause = f"""entry_id = {entry_id}"""
        if lexeme_id:
            if where_clause:
                where_clause = where_clause + " and "
            where_clause = where_clause + f"""lexeme_id = {lexeme_id}"""
        if sense_id:
            if where_clause:
                where_clause = where_clause + " and "
            where_clause = where_clause + f"""sense_id = {sense_id}"""
        sql_sources = f"""
    SELECT abbr, title, url, data->'sourceDetails' as details
    FROM {DbConnectionInfo.schema}.source_links scl
    JOIN {DbConnectionInfo.schema}.sources sc ON scl.source_id = sc.id
    WHERE {where_clause}
    ORDER BY order_no
    """
        cursor.execute(sql_sources)
        sources = cursor.fetchall()
        if not sources:
            return []
        result = []
        for db_row in sources:
            source = DictSource(db_row['abbr'], db_row['title'], db_row['url'], db_row['details'])
            result.append(source)
        return result
