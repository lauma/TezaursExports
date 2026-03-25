from functools import reduce
from typing import Optional, Generator
from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.gram import GramInfo
from lv.ailab.tezaurs.dbobjects.relations import ExternalRelation
from lv.ailab.tezaurs.dbobjects.senses import Sense
from lv.ailab.tezaurs.dbobjects.sources import DictSource
from lv.ailab.tezaurs.dbobjects.wordforms import Wordform


class Lexeme:
    def __init__(self, db_id : int, lemma : str, hidden : bool, lexeme_type : Optional[str] = None):
        self.dbId : int = db_id
        self.lemma : str = lemma
        self.type : Optional[str] = lexeme_type
        self.hidden : bool = hidden

        self.gramInfo : GramInfo = GramInfo()

        self.pronunciations : list[str] = []
        self.sources : list[DictSource] = []
        self.synsetIds : set[int] = set()
        self.externalSynsetIds : set[str] = set()
        self.wordforms : list[Wordform] = []

        self.parentEntryDbId : Optional[int] = None
        self.parentEntryHK : Optional[str] = None


    @staticmethod
    def fetch_lexemes(connection : DbConnection, entry_id : int, main_lex_id : int) -> list[Lexeme]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_senses = f"""
    SELECT l.id, lemma, lt.name as lexeme_type, p.human_key as paradigm, stem1, stem2, stem3,
        l.data, p.data as paradigm_data, l.hidden
    FROM {DbConnectionInfo.schema}.lexemes l
    JOIN {DbConnectionInfo.schema}.lexeme_types lt ON l.type_id = lt.id
    LEFT OUTER JOIN {DbConnectionInfo.schema}.paradigms p ON l.paradigm_id = p.id
    WHERE entry_id = {entry_id} and (NOT hidden or reason_for_hiding='not-public')
    ORDER BY (l.id!={main_lex_id}), order_no
    """
        cursor.execute(sql_senses)
        lexemes = cursor.fetchall()
        if not lexemes:
            return []
        result = []
        for db_row in lexemes:
            lexeme = Lexeme(db_row['id'], db_row['lemma'], db_row['hidden'], db_row['lexeme_type'])
            lexeme.parentEntryDbId = entry_id
            if 'data' in db_row and db_row['data'] and 'Pronunciations' in db_row['data']:
                lexeme.pronunciations = db_row['data']['Pronunciations']
            lexeme.gramInfo = GramInfo.extract_gram(
                db_row, {'Stems', 'Morfotabulas tips', 'Paradigmas īpatnības'})
            lexeme.sources = DictSource.fetch_sources_by_esl_id(
                connection, None, db_row['id'], None)
            result.append(lexeme)
        return result


    @staticmethod
    def fetch_synset_lexemes(connection : DbConnection, synset_id : int) -> list[Lexeme]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_synset_lexemes = f"""
    SELECT syn.id,
        l.id as lexeme_id, l.lemma as lemma, l.hidden, e.id as entry_id, e.human_key as entry_hk
    FROM {DbConnectionInfo.schema}.synsets syn
    RIGHT OUTER JOIN {DbConnectionInfo.schema}.senses s ON syn.id = s.synset_id
    RIGHT OUTER JOIN {DbConnectionInfo.schema}.lexemes l ON s.entry_id = l.entry_id
    JOIN {DbConnectionInfo.schema}.lexeme_types lt on l.type_id = lt.id
    JOIN {DbConnectionInfo.schema}.entries e ON s.entry_id = e.id
    WHERE syn.id = {synset_id}
          and (NOT s.hidden or s.reason_for_hiding='not-public')
          and (NOT l.hidden or l.reason_for_hiding='not-public')
          and (NOT e.hidden or e.reason_for_hiding='not-public') and
          (lt.name = 'default' or lt.name = 'alternativeSpelling' or lt.name = 'abbreviation')
    ORDER BY e.type_id, entry_hk
    """
        cursor.execute(sql_synset_lexemes)
        lexemes = cursor.fetchall()
        result = []
        for db_row in lexemes:
            lexeme = Lexeme(db_row['lexeme_id'], db_row['lemma'], db_row['hidden'])
            lexeme.parentEntryDbId = db_row['entry_id']
            lexeme.parentEntryHK = db_row['entry_hk']
            result.append(lexeme)
        return result


    @staticmethod
    def fetch_all_synseted_lexemes(connection : DbConnection) -> Generator[Lexeme]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_synset_lexemes = f"""
    SELECT l.id AS id, l.entry_id AS entry_id, l.lemma AS lemma,
        l.data, p.data AS paradigm_data, l.hidden,
        p.human_key AS paradigm, stem1, stem2, stem3, e.human_key AS entry_hk
    FROM {DbConnectionInfo.schema}.lexemes AS l
    JOIN {DbConnectionInfo.schema}.lexeme_types lt ON l.type_id = lt.id
    LEFT JOIN {DbConnectionInfo.schema}.paradigms p ON l.paradigm_id = p.id
    JOIN {DbConnectionInfo.schema}.entries e ON l.entry_id = e.id
    JOIN {DbConnectionInfo.schema}.senses s ON l.entry_id = s.entry_id
    WHERE s.synset_id IS NOT NULL
          AND (NOT l.hidden OR l.reason_for_hiding='not-public')
          AND (NOT s.hidden OR s.reason_for_hiding='not-public')
          AND (NOT e.hidden OR e.reason_for_hiding='not-public') 
          AND (lt.name = 'default' OR lt.name = 'alternativeSpelling' OR lt.name = 'abbreviation')
    GROUP BY l.id, l.data, p.data, p.human_key, e.human_key
    ORDER BY l.lemma ASC, p.human_key ASC, e.human_key, l.id
    """
        cursor.execute(sql_synset_lexemes)
        counter = 0
        while True:
            synseted_lexemes = cursor.fetchmany(1000)
            if not synseted_lexemes:
                break
            for db_row in synseted_lexemes:
                counter = counter + 1
                result = Lexeme(db_row['id'], db_row['lemma'], db_row['hidden'])
                result.parentEntryDbId = db_row['entry_id']
                result.parentEntryHK = db_row['entry_hk']
                result.gramInfo = GramInfo.extract_gram(db_row)
                yield result
            print(f'lexemes: {counter}\r')


    @staticmethod
    def fetch_all_lexemes_with_paradigms_and_synsets(connection : DbConnection) -> Generator[Lexeme]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_lexemes = f"""
    SELECT l.id, l.lemma, l.data, p.data as paradigm_data, p.human_key as paradigm,
        stem1, stem2, stem3, l.hidden
    FROM {DbConnectionInfo.schema}.lexemes l
    JOIN {DbConnectionInfo.schema}.paradigms p ON l.paradigm_id = p.id 
    JOIN {DbConnectionInfo.schema}.entries e ON l.entry_id = e.id 
    WHERE (NOT l.hidden OR l.reason_for_hiding='not-public')
        AND (NOT e.hidden OR e.reason_for_hiding='not-public') 
    ORDER BY l.lemma, p.human_key 
    """
        cursor.execute(sql_lexemes)
        counter = 0
        while True:
            para_synseted_lexemes = cursor.fetchmany(1000)
            if not para_synseted_lexemes:
                break
            for db_row in para_synseted_lexemes:
                counter = counter + 1
                result = Lexeme(db_row['id'], db_row['lemma'], db_row['hidden'])
                result.gramInfo = GramInfo.extract_gram(db_row)
                result.wordforms = Wordform.fetch_wordforms(connection, db_row['id'])
                synset_senses = Sense.fetch_synseted_senses_by_lexeme(connection, db_row['id'])
                synset_ids = set(map(lambda a: a.synset.dbId if a.synset else {},
                                     synset_senses)) if synset_senses else {}
                external_synset_ids = set(map(lambda a: a.remoteId, reduce(
                    lambda a, b: a + b,
                    map(lambda a: ExternalRelation.fetch_exteral_synset_eq_relations(connection, a), synset_ids),
                    [])))
                result.synsetIds = synset_ids
                result.externalSynsetIds = external_synset_ids
                yield result
            print(f'lexemes: {counter}\r')

