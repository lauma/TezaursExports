from typing import Optional, NamedTuple

from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbobjects.gram import GramInfo
from lv.ailab.tezaurs.dbobjects.sources import DictSource


class Lexeme:
    def __init__(self, db_id, lemma, hidden, type = None):
        self.dbId : int = db_id
        self.lemma : str = lemma
        self.type : Optional[str] = type
        self.hidden : bool = hidden

        self.gramInfo : Optional[GramInfo] = None

        self.pronunciations : list[str] = []
        self.sources : list[DictSource] = []


    @staticmethod
    def fetch_lexemes(connection : DbConnection, entry_id : int, main_lex_id : int) -> list[Lexeme]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_senses = f"""
    SELECT l.id, lemma, lt.name as lexeme_type, p.human_key as paradigm, stem1, stem2, stem3,
        l.data, p.data as paradigm_data, hidden
    FROM {db_connection_info['schema']}.lexemes l
    JOIN {db_connection_info['schema']}.lexeme_types lt ON l.type_id = lt.id
    LEFT OUTER JOIN {db_connection_info['schema']}.paradigms p ON l.paradigm_id = p.id
    WHERE entry_id = {entry_id} and (NOT hidden or reason_for_hiding='not-public')
    ORDER BY (l.id!={main_lex_id}), order_no
    """
        cursor.execute(sql_senses)
        lexemes = cursor.fetchall()
        if not lexemes:
            return []
        result = []
        for lexeme_row in lexemes:
            lexeme = Lexeme(lexeme_row.id, lexeme_row.lemma, lexeme_row.hidden, lexeme_row.lexeme_type)
            if lexeme_row.data and 'Pronunciations' in lexeme_row.data:
                lexeme.pronunciations = lexeme_row.data['Pronunciations']
            lexeme.gramInfo = GramInfo.extract_gram(
                lexeme_row, {'Stems', 'Morfotabulas tips', 'Paradigmas īpatnības'})
            lexeme.sources = DictSource.fetch_sources_by_esl_id(
                connection, None, lexeme_row.id, None)
            result.append(lexeme)
        return result
