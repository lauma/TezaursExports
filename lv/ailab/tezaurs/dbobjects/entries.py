from typing import Generator, Optional
from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbaccess.single_entry_queries import fetch_morpho_derivs
from lv.ailab.tezaurs.dbobjects.examples import Example
from lv.ailab.tezaurs.dbobjects.gram import GramInfo
from lv.ailab.tezaurs.dbobjects.lexemes import Lexeme
from lv.ailab.tezaurs.dbobjects.senses import Sense
from lv.ailab.tezaurs.dbobjects.sources import DictSource


class Entry:
    def __init__(self, db_id, homonym, entry_type, headword, hidden):
        self.dbId : int = db_id
        self.hidden : bool = hidden

        self.homonym : int = homonym
        self.type : str = entry_type
        self.headword : str = headword
        self.etymology : Optional[str] = None

        self.gram : Optional[GramInfo] = None

        self.lexemes : list [Lexeme] = []
        self.senses : list[Sense] = []
        self.examples : list[Example] = []
        self.sources : list[DictSource] = []

        self.morphoDerivatives = None

    @staticmethod
    def fetch_all_entries(connection : DbConnection, omit_mwe : bool = False, omit_wordparts : bool = False,
                          omit_pot_wordparts : bool = False,
                          do_entrylevel_exmples : bool = False) -> Generator[Entry]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        where_clause = ""
        if omit_mwe or omit_wordparts:
            where_clause = """et.name = 'word'"""
            if not omit_wordparts:
                where_clause = where_clause + """ or et.name = 'wordPart'"""
            if not omit_mwe:
                where_clause = where_clause + """ or et.name = 'mwe'"""
            where_clause = '(' + where_clause + ')' + " and"
        sql_entries = f"""
    SELECT e.id, type_id, name as type_name, heading, human_key, homonym_no,
        primary_lexeme_id, e.data->>'Etymology' as etym, e.data as data, e.hidden
    FROM {db_connection_info['schema']}.entries e
    JOIN {db_connection_info['schema']}.entry_types et ON e.type_id = et.id
    WHERE {where_clause} (NOT e.hidden or e.reason_for_hiding='not-public')
    ORDER BY type_id, heading, homonym_no
    """
        cursor.execute(sql_entries)
        counter = 0
        while True:
            rows = cursor.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                counter = counter + 1
                result = Entry(row.human_key, row.homonym_no, row.type_name, row.heading, row.hidden)
                if row.etym:
                    result.etymology = row.etym
                result.gram = GramInfo.extract_gram(row, None)

                lexemes = Lexeme.fetch_lexemes(connection, row.id, row.primary_lexeme_id)
                if lexemes:
                    result.lexemes = lexemes
                # primary_lexeme = fetch_main_lexeme(connection, row.primary_lexeme_id, row.human_key)
                primary_lexeme = lexemes[0]
                if not primary_lexeme:
                    continue
                if omit_pot_wordparts and \
                        (row.type_name == 'wordPart' or primary_lexeme.lemma.startswith('-') or
                         primary_lexeme.lemma.endswith('-')):
                    continue
                result.senses = Sense.fetch_senses(connection, row.id)
                if do_entrylevel_exmples:
                    result.examples = Example.fetch_examples(connection, row.id, True)
                result.sources = DictSource.fetch_sources_by_esl_id(connection, row.id)
                morpho_derivs = fetch_morpho_derivs(connection, row.id)
                if morpho_derivs:
                    result.morphoDerivatives = morpho_derivs
                yield result
            print(f'entries: {counter}\r')
