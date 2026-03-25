from typing import Optional, Generator
import regex
from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.examples import Example
from lv.ailab.tezaurs.dbobjects.gram import GramInfo
from lv.ailab.tezaurs.dbobjects.relations import NamedInternalRelation, ExternalRelation, GlossLink
from lv.ailab.tezaurs.dbobjects.sources import DictSource


class Sense:
    def __init__(self, db_id : int, ord_no : int, gloss : str, hidden : bool):
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
    def fetch_senses(connection : DbConnection, entry_id : int, parent_sense_id : int = None) -> list[Sense]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        parent_sense_clause = 'is NULL'
        if parent_sense_id:
            parent_sense_clause = f"""= {parent_sense_id}"""
        sql_senses = f"""
    SELECT id, gloss, order_no, parent_sense_id, synset_id, data, hidden
    FROM {DbConnectionInfo.schema}.senses
    WHERE entry_id = {entry_id} and parent_sense_id {parent_sense_clause} and (NOT hidden or reason_for_hiding='not-public')
    ORDER BY order_no
    """
        cursor.execute(sql_senses)
        senses = cursor.fetchall()
        if not senses:
            return []
        result = []
        for db_row in senses:
            sense_id = db_row['id']
            gloss = db_row['gloss']
            synset_id = db_row['synset_id'] if 'synset_id' in db_row else None
            sense = Sense(sense_id, db_row['order_no'], gloss, db_row['hidden'])
            sense.gram = GramInfo.extract_gram(db_row, None)
            if synset_id:
                sense.synset = Synset(
                    db_row['synset_id'],
                    Sense.fetch_synset_senses(connection, synset_id),
                    NamedInternalRelation.fetch_synset_relations(connection, synset_id),
                    Gradset.fetch_gradset(connection, synset_id),
                    ExternalRelation.fetch_exteral_synset_eq_relations(connection, synset_id),
                    ExternalRelation.fetch_exteral_synset_neq_relations(connection, synset_id))
            sense.subsenses = Sense.fetch_senses(connection, entry_id, sense_id)
            sense.examples = Example.fetch_examples(connection, sense_id)
            sense.semanticDerivatives = NamedInternalRelation.fetch_semantic_derivs_by_sense(connection, sense_id)
            sense.sources = DictSource.fetch_sources_by_esl_id(connection, None, None, sense_id)

            if regex.search(r'\[((?:\p{L}\p{M}*)+)\]\{e:\d+\}', gloss):
                sense.glossToEntryLinks = GlossLink.fetch_gloss_entry_links(connection, sense_id)
            if regex.search(r'\[((?:\p{L}\p{M}*)+)\]\{s:\d+\}', gloss):
                sense.glossToSenseLinks = GlossLink.fetch_gloss_sense_links(connection, sense_id)

            result.append(sense)
        return result


    @staticmethod
    def fetch_synset_senses(connection : DbConnection, synset_id : int) -> list[Sense]:
        if not synset_id:
            return []
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_synset_senses = f"""
    SELECT syn.id, s.id as sense_id, s.order_no as sense_no, s.gloss, s.hidden,
           sp.order_no as parent_sense_no, e.human_key as entry_hk
    FROM {DbConnectionInfo.schema}.synsets syn
    RIGHT OUTER JOIN dict.senses s ON syn.id = s.synset_id
    LEFT OUTER JOIN dict.senses sp ON s.parent_sense_id = sp.id
    JOIN {DbConnectionInfo.schema}.entries e ON s.entry_id = e.id
    WHERE syn.id = {synset_id} and (NOT s.hidden or s.reason_for_hiding='not-public')
    ORDER BY e.type_id, entry_hk
    """
        cursor.execute(sql_synset_senses)
        synset_members = cursor.fetchall()
        if not synset_members:
            return []
        result = []
        for db_row in synset_members:
            entry_hk = db_row['entry_hk']
            sense_no = db_row['sense_no']
            sense = Sense(db_row['sense_id'], sense_no, db_row['gloss'], db_row['hidden'])
            if 'parent_sense_no' in db_row and db_row['parent_sense_no']:
                sense.calculatedHumanId = f"{entry_hk}/{db_row['parent_sense_no']}/{sense_no}"
            else:
                sense.calculatedHumanId = f"{entry_hk}/{sense_no}"
            sense.examples = Example.fetch_examples(connection, db_row['sense_id'])
            result.append(sense)
        return result


    @staticmethod
    def fetch_synseted_senses_by_lexeme(connection : DbConnection, lexeme_id : int) -> list[Sense]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_senses = f"""
    SELECT s.id AS sense_id, s.order_no, s.gloss, s.hidden, s.synset_id
    FROM {DbConnectionInfo.schema}.senses s
    JOIN {DbConnectionInfo.schema}.lexemes l ON s.entry_id = l.entry_id
    WHERE l.id = {lexeme_id} AND s.synset_id IS NOT NULL AND (NOT s.hidden OR s.reason_for_hiding='not-public')
    """
        cursor.execute(sql_senses)
        senses = cursor.fetchall()
        if not senses:
            return []
        result = []
        for db_row in senses:
            sense = Sense(db_row['sense_id'], db_row['order_no'], db_row['gloss'], db_row['hidden'])
            sense.synset = Synset(db_row['synset_id'], [])
            result.append(sense)
        return result



class Synset:
    def __init__ (self, db_id : int, senses : list[Sense],
                  relations : Optional[list[NamedInternalRelation]] = None,
                  gradset : Optional[Gradset] = None,
                  ext_eq_rels : Optional[list[ExternalRelation]] = None,
                  ext_neq_rels : Optional[list[ExternalRelation]] = None):
        self.dbId : int = db_id
        self.senses : list[Sense] = senses
        self.relations : list[NamedInternalRelation] = [] if relations is None else relations
        self.gradset : Optional[Gradset] = gradset
        self.externalEqRelations : list[ExternalRelation] = [] if ext_eq_rels is None else ext_eq_rels
        self.externalNeqRelations : list[ExternalRelation] = [] if ext_neq_rels is None else ext_neq_rels


    @staticmethod
    def fetch_all_synsets(connection : DbConnection, filter_ext_rel_by : str = None) -> Generator[Synset]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_synset = f"""
    SELECT syn.id
    FROM {DbConnectionInfo.schema}.synsets as syn
    JOIN {DbConnectionInfo.schema}.senses as s ON syn.id = s.synset_id
    GROUP BY syn.id
    ORDER BY id ASC
    """
        cursor.execute(sql_synset)
        counter = 0
        while True:
            synsets = cursor.fetchmany(1000)
            if not synsets:
                break
            for db_row in synsets:
                counter = counter + 1
                synset_id = db_row['id']
                yield Synset (synset_id,
                              Sense.fetch_synset_senses(connection, synset_id),
                              NamedInternalRelation.fetch_synset_relations(connection, synset_id),
                              Gradset.fetch_gradset(connection, synset_id),
                              ExternalRelation.fetch_exteral_synset_eq_relations(connection, synset_id, filter_ext_rel_by),
                              ExternalRelation.fetch_exteral_synset_neq_relations(connection, synset_id, filter_ext_rel_by))
            print(f'synsets: {counter}\r')



class Gradset:
    def __init__(self, db_id : int, gradset_category : str, member_synset_ids : list[int]):
        self.dbId : int = db_id
        self.category : str = gradset_category
        self.memberIds : list[int] = member_synset_ids


    @staticmethod
    def fetch_gradset(connection : DbConnection, member_synset_id : int) -> Optional[Gradset]:
        if not member_synset_id:
            return None

        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_gradset = f"""
    SELECT syn.id as synset_id, syn.gradset_id as gradset_id, grad.synset_id as gradset_cat
    FROM  {DbConnectionInfo.schema}.synsets syn
    JOIN {DbConnectionInfo.schema}.gradsets grad ON syn.gradset_id = grad.id
    WHERE gradset_id = (
        SELECT gradset_id
        FROM {DbConnectionInfo.schema}.synsets
        WHERE ID = {member_synset_id}) AND gradset_id is not null
    ORDER BY syn.id
    """
        cursor.execute(sql_gradset)
        gradset_members = cursor.fetchall()
        if not gradset_members:
            return None

        result = Gradset(gradset_members[0]['gradset_id'], gradset_members[0]['gradset_cat'], [])
        for member in gradset_members:
            result.memberIds.append(member['synset_id'])
        return result
