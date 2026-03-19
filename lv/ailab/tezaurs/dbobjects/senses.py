from typing import Optional, Generator
import regex
from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbobjects.examples import Example
from lv.ailab.tezaurs.dbobjects.gram import GramInfo
from lv.ailab.tezaurs.dbobjects.relations import NamedInternalRelation, ExternalRelation, GlossLink
from lv.ailab.tezaurs.dbobjects.sources import DictSource


class Sense:
    def __init__(self, db_id, ord_no, gloss, hidden):
        self.dbId : int = db_id
        self.calculatedHumanId : Optional[str] = None
        self.orderNo : int = ord_no
        self.hidden : bool = hidden
        self.gloss : str = gloss

        self.synset : Optional[Synset] = None
        self.gram : GramInfo = GramInfo()

        self.examples : list[Example] = []
        self.subsenses : list[Sense] = []
        self.sources : list[DictSource] = []

        self.semanticDerivatives : list[NamedInternalRelation] = []
        self.glossToEntryLinks : dict[int, GlossLink] = {}
        self.glossToSenseLinks : dict[int, GlossLink] = {}


    @staticmethod
    def fetch_senses(connection : DbConnection, entry_id : int, parent_sense_id : int = None)\
            -> list[Sense]:
        if not entry_id:
            return []
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        parent_sense_clause = 'is NULL'
        if parent_sense_id:
            parent_sense_clause = f"""= {parent_sense_id}"""
        sql_senses = f"""
    SELECT id, gloss, order_no, parent_sense_id, synset_id, data, hidden
    FROM {db_connection_info['schema']}.senses
    WHERE entry_id = {entry_id} and parent_sense_id {parent_sense_clause} and (NOT hidden or reason_for_hiding='not-public')
    ORDER BY order_no
    """
        cursor.execute(sql_senses)
        senses = cursor.fetchall()
        if not senses:
            return []
        result = []
        for sense_data in senses:
            sense = Sense(sense_data.id, sense_data.order_no, sense_data.gloss, sense_data.hidden)
            sense.gram = GramInfo.extract_gram(sense_data, None)
            if sense_data.synset_id:
                sense.synset = Synset(
                    sense_data.synset_id,
                    Sense.fetch_synset_senses(connection, sense_data.synset_id),
                    NamedInternalRelation.fetch_synset_relations(connection, sense_data.synset_id),
                    Gradset.fetch_gradset(connection, sense_data.synset_id),
                    ExternalRelation.fetch_exteral_synset_eq_relations(connection, sense_data.synset_id),
                    ExternalRelation.fetch_exteral_synset_neq_relations(connection, sense_data.synset_id))
            sense.subsenses = Sense.fetch_senses(connection, entry_id, sense_data.id)
            sense.examples = Example.fetch_examples(connection, sense_data.id)
            sense.semanticDerivatives = NamedInternalRelation.fetch_semantic_derivs_by_sense(connection, sense_data.id)
            sense.sources = DictSource.fetch_sources_by_esl_id(connection, None, None, sense_data.id)

            if regex.search(r'\[((?:\p{L}\p{M}*)+)\]\{e:\d+\}', sense_data.gloss):
                sense.glossToEntryLinks = GlossLink.fetch_gloss_entry_links(connection, sense_data.id)
            if regex.search(r'\[((?:\p{L}\p{M}*)+)\]\{s:\d+\}', sense_data.gloss):
                sense.glossToSenseLinks = GlossLink.fetch_gloss_sense_links(connection, sense_data.id)

            result.append(sense)
        return result


    @staticmethod
    def fetch_synset_senses(connection : DbConnection, synset_id : int) -> list[Sense]:
        if not synset_id:
            return []
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_synset_senses = f"""
    SELECT syn.id, s.id as sense_id, s.order_no as sense_no, s.gloss, s.hidden,
           sp.order_no as parent_sense_no, e.human_key as entry_hk
    FROM {db_connection_info['schema']}.synsets syn
    RIGHT OUTER JOIN dict.senses s ON syn.id = s.synset_id
    LEFT OUTER JOIN dict.senses sp ON s.parent_sense_id = sp.id
    JOIN {db_connection_info['schema']}.entries e ON s.entry_id = e.id
    WHERE syn.id = {synset_id} and (NOT s.hidden or s.reason_for_hiding='not-public')
    ORDER BY e.type_id, entry_hk
    """
        cursor.execute(sql_synset_senses)
        synset_members = cursor.fetchall()
        if not synset_members:
            return []
        result = []
        for member in synset_members:
            sense = Sense(member.sense_id, member.sense_no, member.gloss, member.hidden)
            # sense_dict = {'hardid': member.sense_id, 'gloss': member.gloss, 'hidden': member.hidden}
            if member.parent_sense_no:
                # sense_dict['softid'] = f'{member.entry_hk}/{member.parent_sense_no}/{member.sense_no}'
                sense.calculatedHumanId = f'{member.entry_hk}/{member.parent_sense_no}/{member.sense_no}'
            else:
                sense.calculatedHumanId = f'{member.entry_hk}/{member.sense_no}'
            sense.examples = Example.fetch_examples(connection, member.sense_id)
            result.append(sense)
        return result


    @staticmethod
    def fetch_synseted_senses_by_lexeme(connection : DbConnection, lexeme_id : int) -> list[Sense]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_senses = f"""
    SELECT s.id as sense_id, s.order_no, s.gloss, s.hidden, s.synset_id
    FROM {db_connection_info['schema']}.senses s
    JOIN {db_connection_info['schema']}.lexemes l on s.entry_id = l.entry_id
    WHERE l.id = {lexeme_id} AND s.synset_id<>0 AND (NOT s.hidden OR s.reason_for_hiding='not-public')
    """
        cursor.execute(sql_senses)
        senses = cursor.fetchall()
        if not senses:
            return []
        result = []
        for s in senses:
            sense = Sense(s.sense_id, s.order_no, s.gloss, s.hidden)
            if s.synset_id:
                sense.synset = Synset(s.synset_id, None)
            result.append(sense)
            #result.append({'sense_id': s.sense_id, 'synset_id': s.synset_id})
        return result



class Synset:
    def __init__ (self, db_id, senses, relations = None, gradset = None, ext_eq_rels = None, ext_neq_rels = None):
        self.dbId : int = db_id
        self.senses : list[Sense] = senses
        self.relations : list[NamedInternalRelation] = [] if relations is None else relations
        self.gradset : Optional[Gradset] = gradset
        self.externalEqRelations : list[ExternalRelation] = [] if ext_eq_rels is None else ext_eq_rels
        self.externalNeqRelations : list[ExternalRelation] = [] if ext_neq_rels is None else ext_neq_rels


    @staticmethod
    def fetch_all_synsets(connection : DbConnection, filter_ext_rel_by : str = None) -> Generator[Synset]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_synset = f"""
    SELECT syn.id
    FROM {db_connection_info['schema']}.synsets as syn
    JOIN {db_connection_info['schema']}.senses as s ON syn.id = s.synset_id
    GROUP BY syn.id
    ORDER BY id ASC
    """
        cursor.execute(sql_synset)
        counter = 0
        while True:
            rows = cursor.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                counter = counter + 1
                yield Synset (row.id,
                              Sense.fetch_synset_senses(connection, row.id),
                              NamedInternalRelation.fetch_synset_relations(connection, row.id),
                              Gradset.fetch_gradset(connection, row.id),
                              ExternalRelation.fetch_exteral_synset_eq_relations(connection, row.id, filter_ext_rel_by),
                              ExternalRelation.fetch_exteral_synset_neq_relations(connection, row.id, filter_ext_rel_by))
            print(f'synsets: {counter}\r')



class Gradset:
    def __init__(self, db_id, gradset_category, member_synset_ids):
        self.dbId : int = db_id
        self.category : str = gradset_category
        self.memberIds : list[int] = member_synset_ids


    @staticmethod
    def fetch_gradset(connection : DbConnection, member_synset_id : int) -> Optional[Gradset]:
        if not member_synset_id:
            return None

        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_gradset = f"""
    SELECT syn.id as synset_id, syn.gradset_id as gradset_id, grad.synset_id as gradset_cat
    FROM  {db_connection_info['schema']}.synsets syn
    JOIN {db_connection_info['schema']}.gradsets grad ON syn.gradset_id = grad.id
    WHERE gradset_id = (
        SELECT gradset_id
        FROM {db_connection_info['schema']}.synsets
        WHERE ID = {member_synset_id}) AND gradset_id is not null
    ORDER BY syn.id
    """
        cursor.execute(sql_gradset)
        gradet_members = cursor.fetchall()
        if not gradet_members:
            return None

        result = Gradset(gradet_members[0].gradset_id, gradet_members[0].gradset_cat, [])
        for member in gradet_members:
            result.memberIds.append(member.synset_id)
        return result
