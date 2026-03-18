from functools import reduce
from typing import Optional, Generator
from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbaccess.single_synset_queries import fetch_exteral_synset_eq_relations
from lv.ailab.tezaurs.dbaccess.subentry_queries import fetch_synseted_senses_by_lexeme
from lv.ailab.tezaurs.dbobjects.gram import GramInfo
from lv.ailab.tezaurs.dbobjects.sources import DictSource
from lv.ailab.tezaurs.dbobjects.wordforms import Wordform


class Lexeme:
    def __init__(self, db_id, lemma, hidden, type = None):
        self.dbId : int = db_id
        self.lemma : str = lemma
        self.type : Optional[str] = type
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
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_senses = f"""
    SELECT l.id, lemma, lt.name as lexeme_type, p.human_key as paradigm, stem1, stem2, stem3,
        l.data, p.data as paradigm_data, l.hidden
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
            lexeme.parentEntryDbId = entry_id
            if lexeme_row.data and 'Pronunciations' in lexeme_row.data:
                lexeme.pronunciations = lexeme_row.data['Pronunciations']
            lexeme.gramInfo = GramInfo.extract_gram(
                lexeme_row, {'Stems', 'Morfotabulas tips', 'Paradigmas īpatnības'})
            lexeme.sources = DictSource.fetch_sources_by_esl_id(
                connection, None, lexeme_row.id, None)
            result.append(lexeme)
        return result


    @staticmethod
    def fetch_synset_lexemes(connection : DbConnection, synset_id : int) -> list[Lexeme]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_synset_lexemes = f"""
    SELECT syn.id,
        l.id as lexeme_id, l.lemma as lemma, l.hidden, e.id as entry_id, e.human_key as entry_hk
    FROM {db_connection_info['schema']}.synsets syn
    RIGHT OUTER JOIN {db_connection_info['schema']}.senses s ON syn.id = s.synset_id
    RIGHT OUTER JOIN {db_connection_info['schema']}.lexemes l ON s.entry_id = l.entry_id
    JOIN {db_connection_info['schema']}.lexeme_types lt on l.type_id = lt.id
    JOIN {db_connection_info['schema']}.entries e ON s.entry_id = e.id
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
        for lexemeRow in lexemes:
            lexeme = Lexeme(lexemeRow.lexeme_id, lexemeRow.lemma, lexemeRow.hidden)
            lexeme.parentEntryDbId = lexemeRow.entry_id
            lexeme.parentEntryHK = lexemeRow.entry_hk
            result.append(lexeme)
        return result


    @staticmethod
    def fetch_all_synseted_lexemes(connection : DbConnection) -> Generator[Lexeme]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_synset_lexemes = f"""
    SELECT l.id as id, l.entry_id as entry_id, l.lemma as lemma,
        l.data, p.data as paradigm_data, l.hidden,
        p.human_key as paradigm, stem1, stem2, stem3, e.human_key as entry_hk
    FROM {db_connection_info['schema']}.lexemes as l
    JOIN {db_connection_info['schema']}.lexeme_types lt on l.type_id = lt.id
    LEFT JOIN {db_connection_info['schema']}.paradigms p on l.paradigm_id = p.id
    JOIN {db_connection_info['schema']}.entries e on l.entry_id = e.id
    JOIN {db_connection_info['schema']}.senses s on l.entry_id = s.entry_id
    WHERE s.synset_id <> 0
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
            rows = cursor.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                counter = counter + 1
                result = Lexeme(row.id, row.lemma, row.hidden)
                result.parentEntryDbId = row.entry_id
                result.parentEntryHK = row.entry_hk
                result.gramInfo = GramInfo.extract_gram(row)
                yield result
            print(f'lexemes: {counter}\r')


    @staticmethod
    def fetch_all_lexemes_with_paradigms_and_synsets(connection : DbConnection) -> Generator[Lexeme]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_lexemes = f"""
    SELECT l.id, l.lemma, l.data, p.data as paradigm_data, p.human_key as paradigm,
        stem1, stem2, stem3, l.hidden
    FROM {db_connection_info['schema']}.lexemes l
    JOIN {db_connection_info['schema']}.paradigms p ON l.paradigm_id = p.id 
    JOIN {db_connection_info['schema']}.entries e ON l.entry_id = e.id 
    WHERE (NOT l.hidden OR l.reason_for_hiding='not-public')
        AND (NOT e.hidden OR e.reason_for_hiding='not-public') 
    ORDER BY l.lemma, p.human_key 
    """
        cursor.execute(sql_lexemes)
        counter = 0
        while True:
            rows = cursor.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                counter = counter + 1
                result = Lexeme(row.id, row.lemma, row.hidden)
                result.gramInfo = GramInfo.extract_gram(row)
                result.wordforms = Wordform.fetch_wordforms(connection, row.id)
                synset_senses = fetch_synseted_senses_by_lexeme(connection, row.id)
                synset_ids = set(map(lambda a: a['synset_id'] if 'synset_id' in a else {},
                                     synset_senses)) if synset_senses else {}
                external_synset_ids = set(map(lambda a: a['id'], reduce(
                    lambda a, b: a + b,
                    map(lambda a: fetch_exteral_synset_eq_relations(connection, a), synset_ids),
                    [])))
                result.synsetIds = synset_ids
                result.externalSynsetIds = external_synset_ids
                yield result
            print(f'lexemes: {counter}\r')

