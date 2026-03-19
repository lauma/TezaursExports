from typing import Generator, Optional

from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.examples import Example
from lv.ailab.tezaurs.dbobjects.gram import GramInfo
from lv.ailab.tezaurs.dbobjects.lexemes import Lexeme
from lv.ailab.tezaurs.dbobjects.relations import NamedInternalRelation
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

        self.gram : GramInfo = GramInfo()

        self.lexemes : list [Lexeme] = []
        self.senses : list[Sense] = []
        self.examples : list[Example] = []
        self.sources : list[DictSource] = []
        self.morphoDerivatives : list[NamedInternalRelation] = []

    @staticmethod
    def fetch_all_entries(connection : DbConnection, omit_mwe : bool = False, omit_wordparts : bool = False,
                          omit_pot_wordparts : bool = False,
                          do_entrylevel_exmples : bool = False) -> Generator[Entry]:
        cursor = connection.cursor(cursor_factory=DictCursor)
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
    FROM {DbConnectionInfo.schema}.entries e
    JOIN {DbConnectionInfo.schema}.entry_types et ON e.type_id = et.id
    WHERE {where_clause} (NOT e.hidden or e.reason_for_hiding='not-public')
    ORDER BY type_id, heading, homonym_no
    """
        cursor.execute(sql_entries)
        counter = 0
        while True:
            entries = cursor.fetchmany(1000)
            if not entries:
                break
            for db_row in entries:
                counter = counter + 1
                result = Entry(db_row['human_key'], db_row['homonym_no'], db_row['type_name'], db_row['heading'], db_row['hidden'])
                if 'etym' in db_row:
                    result.etymology = db_row['etym']
                result.gram = GramInfo.extract_gram(db_row, None)

                lexemes = Lexeme.fetch_lexemes(connection, db_row['id'], db_row['primary_lexeme_id'])
                if lexemes:
                    result.lexemes = lexemes
                # primary_lexeme = fetch_main_lexeme(connection, row.primary_lexeme_id, row.human_key)
                primary_lexeme = lexemes[0]
                if not primary_lexeme:
                    continue
                if omit_pot_wordparts and \
                        (db_row['type_name'] == 'wordPart' or primary_lexeme.lemma.startswith('-') or
                         primary_lexeme.lemma.endswith('-')):
                    continue
                result.senses = Sense.fetch_senses(connection, db_row['id'])
                if do_entrylevel_exmples:
                    result.examples = Example.fetch_examples(connection, db_row['id'], True)
                result.sources = DictSource.fetch_sources_by_esl_id(connection, db_row['id'])
                morpho_derivs = NamedInternalRelation.fetch_morpho_derivs(connection, db_row['id'])
                if morpho_derivs:
                    result.morphoDerivatives = morpho_derivs
                yield result
            print(f'entries: {counter}\r')
