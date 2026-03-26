from typing import Optional
from psycopg2.extras import DictCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.gram import GramInfo


class NamedInternalRelation:
    def __init__(self, my_role : str, target_role : str, hidden : bool, target_db_id : int,
                 target_entry_hk : Optional[str] = None, target_soft_id : Optional[str] = None ):
        self.myRole : str = my_role
        self.targetRole : str = target_role
        self.targetSoftId : Optional[str] = target_soft_id
        self.targetDbId : int = target_db_id
        self.targetEntryHk : Optional[str] = target_entry_hk
        self.relationLabel : Optional[str] = None
        self.hidden : bool = hidden
        self.gramInfo : GramInfo = GramInfo()


    @staticmethod
    def fetch_morpho_derivs(connection : DbConnection, entry_id : int) -> list[NamedInternalRelation]:
        result = []
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_derivs_from = f"""
    SELECT er.id, ert.name, ert.name_inverse, e2.id as end_id, e2.human_key as end_human_key,
           er.data as data, er.hidden
    FROM {DbConnectionInfo.schema}.entry_relations er
    JOIN {DbConnectionInfo.schema}.entry_rel_types ert on type_id = ert.id
    JOIN {DbConnectionInfo.schema}.entries e2 on entry_2_id = e2.id
    WHERE entry_1_id = {entry_id} and ert.name = 'derivativeOf'
          and (NOT er.hidden or er.reason_for_hiding='not-public')
          and (NOT e2.hidden or e2.reason_for_hiding='not-public')
    """
        cursor.execute(sql_derivs_from)
        derivs_from = cursor.fetchall()
        for db_row in derivs_from:
            relation = NamedInternalRelation(db_row['name'], db_row['name_inverse'], db_row['hidden'],
                                             db_row['end_id'], db_row['end_human_key'], db_row['end_human_key'])
            relation.gramInfo = GramInfo.extract_gram(db_row)
            result.append(relation)

        sql_derivs_to = f"""
    SELECT er.id, ert.name, ert.name_inverse, e1.id as end_id, e1.human_key as end_human_key,
           er.data as data, er.hidden
    FROM {DbConnectionInfo.schema}.entry_relations er
    JOIN {DbConnectionInfo.schema}.entry_rel_types ert on type_id = ert.id
    JOIN {DbConnectionInfo.schema}.entries e1 on entry_1_id = e1.id
    WHERE entry_2_id = {entry_id} and ert.name = 'derivativeOf'
          and (NOT er.hidden or er.reason_for_hiding='not-public')
          and (NOT e1.hidden or e1.reason_for_hiding='not-public')
    """
        cursor.execute(sql_derivs_to)
        derivs_to = cursor.fetchall()
        for db_row in derivs_to:
            relation = NamedInternalRelation(db_row['name_inverse'], db_row['name'], db_row['hidden'],
                                             db_row['end_id'], db_row['end_human_key'], db_row['end_human_key'])
            # 2024-09-19 ar valodniekiem WN seminārā tiek runāts, ka loģiskāk
            # ir formantu un celma informāciju redzēt pie atvasinājuma, nevis
            # atvasināmā.
            result.append(relation)

        sorted_result = sorted(result,
                               key=lambda item: (not item.hidden, item.myRole, item.targetRole, item.targetSoftId))
        return sorted_result


    @staticmethod
    def fetch_semantic_derivs_by_sense(connection : DbConnection, sense_id : int, synseted_other_end : bool = False) -> list[NamedInternalRelation]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        result = []

        where_clause_1 = "" if not synseted_other_end else "AND s2.synset_id IS NOT NULL"
        sql_sem_derivs_1 = f"""
    SELECT sr.id, sr.hidden, s2.id AS sense_id, s2.order_no AS sense_no, s2p.order_no AS parent_sense_no,
           e2.human_key AS entry_hk, sr.data->'role_1' #>> '{{}}' AS role1, sr.data->'role_2' #>> '{{}}' AS role2
    FROM {DbConnectionInfo.schema}.sense_relations AS sr
    JOIN {DbConnectionInfo.schema}.sense_rel_types AS srl ON sr.type_id = srl.id
    JOIN {DbConnectionInfo.schema}.senses AS s2 ON sr.sense_2_id = s2.id
    LEFT OUTER JOIN {DbConnectionInfo.schema}.senses s2p ON s2.parent_sense_id = s2p.id
    JOIN {DbConnectionInfo.schema}.entries e2 ON s2.entry_id = e2.id
    WHERE sr.sense_1_id = {sense_id} AND srl.relation_name = 'semanticRelation' 
          AND (NOT sr.hidden OR sr.reason_for_hiding='not-public')
          AND (NOT s2.hidden OR s2.reason_for_hiding='not-public')
          AND (s2p.hidden IS NULL OR NOT s2p.hidden OR s2p.reason_for_hiding='not-public')
          AND (NOT e2.hidden OR e2.reason_for_hiding='not-public')
          {where_clause_1}
    """
        cursor.execute(sql_sem_derivs_1)
        sem_derivs_1 = cursor.fetchall()
        for db_row in sem_derivs_1:
            target_soft_id = f"{db_row['entry_hk']}/{db_row['parent_sense_no']}/{db_row['sense_no']}"\
                if db_row['parent_sense_no'] else f"{db_row['entry_hk']}/{db_row['sense_no']}"
            relation = NamedInternalRelation(db_row['role1'], db_row['role2'], db_row['hidden'],
                                             db_row['sense_id'], db_row['entry_hk'], target_soft_id)
            result.append(relation)

        where_clause_2 = "" if not synseted_other_end else "AND s1.synset_id IS NOT NULL"
        sql_sem_derivs_2 = f"""
    SELECT sr.id, sr.hidden, s1.id AS sense_id, s1.order_no AS sense_no, s1p.order_no AS parent_sense_no,
           e1.human_key AS entry_hk, sr.data->'role_1' #>> '{{}}' AS role1, sr.data->'role_2' #>> '{{}}' AS role2
    FROM {DbConnectionInfo.schema}.sense_relations AS sr
    JOIN {DbConnectionInfo.schema}.sense_rel_types AS srl ON sr.type_id = srl.id
    JOIN {DbConnectionInfo.schema}.senses AS s1 ON sr.sense_1_id = s1.id
    LEFT OUTER JOIN {DbConnectionInfo.schema}.senses s1p ON s1.parent_sense_id = s1p.id
    JOIN {DbConnectionInfo.schema}.entries e1 ON s1.entry_id = e1.id
    WHERE sr.sense_2_id = {sense_id} AND srl.relation_name = 'semanticRelation'
          AND (NOT sr.hidden OR sr.reason_for_hiding='not-public')
          AND (NOT s1.hidden OR s1.reason_for_hiding='not-public')
          AND (s1p.hidden IS NULL OR NOT s1p.hidden OR s1p.reason_for_hiding='not-public')
          AND (NOT e1.hidden OR e1.reason_for_hiding='not-public')
          {where_clause_2}
    """
        cursor.execute(sql_sem_derivs_2)
        sem_derivs_2 = cursor.fetchall()
        for db_row in sem_derivs_2:
            target_soft_id = f"{db_row['entry_hk']}/{db_row['parent_sense_no']}/{db_row['sense_no']}"\
                if db_row['parent_sense_no'] else f"{db_row['entry_hk']}/{db_row['sense_no']}"
            relation = NamedInternalRelation(db_row['role2'], db_row['role1'], db_row['hidden'],
                                             db_row['sense_id'], db_row['entry_hk'], target_soft_id)
            result.append(relation)

        sorted_result = sorted(result,
                               key=lambda item: (not item.hidden, item.myRole, item.targetRole, item.targetSoftId))
        return sorted_result


    @staticmethod
    def fetch_synset_relations(connection : DbConnection, synset_id : int) -> list[NamedInternalRelation]:
        result = []

        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_synset_rels_1 = f"""
    SELECT rel.id, rel.synset_1_id as other, rel.hidden, tp.name, tp.name_inverse, tp.relation_name as rel_name
    FROM {DbConnectionInfo.schema}.synset_relations rel
    JOIN {DbConnectionInfo.schema}.synset_rel_types tp ON rel.type_id = tp.id
    JOIN dict.senses s ON rel.synset_1_id = s.synset_id
    WHERE rel.synset_2_id = {synset_id}
          and (NOT rel.hidden or rel.reason_for_hiding='not-public')
          and (NOT s.hidden or s.reason_for_hiding='not-public')
    GROUP BY rel.id, tp.name_inverse, tp.name, rel_name
    """
        cursor.execute(sql_synset_rels_1)
        relations = cursor.fetchall()
        if relations:
            for db_row in relations:
                relation = NamedInternalRelation(db_row['name_inverse'], db_row['name'], db_row['hidden'],
                                                 db_row['other'])
                relation.relationLabel = db_row['rel_name']
                result.append(relation)

        sql_synset_rels_2 = f"""
    SELECT rel.id, rel.synset_2_id as other, rel.hidden, tp.name, tp.name_inverse, tp.relation_name as rel_name
    FROM {DbConnectionInfo.schema}.synset_relations rel
    JOIN {DbConnectionInfo.schema}.synset_rel_types tp ON rel.type_id = tp.id
    JOIN dict.senses s ON rel.synset_2_id = s.synset_id
    WHERE rel.synset_1_id = {synset_id}
          and (NOT rel.hidden or rel.reason_for_hiding='not-public')
          and (NOT s.hidden or s.reason_for_hiding='not-public')
    GROUP BY rel.id, tp.name, tp.name_inverse, rel_name
    """

        cursor.execute(sql_synset_rels_2)
        relations = cursor.fetchall()
        if relations:
            for db_row in relations:
                relation = NamedInternalRelation(db_row['name'], db_row['name_inverse'], db_row['hidden'],
                                                 db_row['other'])
                relation.relationLabel = db_row['rel_name']
                result.append(relation)

        sorted_result = sorted(result,
                               key=lambda item: (not item.hidden, item.myRole, item.targetRole, item.targetDbId))
        return sorted_result



class GlossLink:
    def __init__(self, target_db_id : int, target_soft_id : Optional[str] = None):
        self.targetSoftId: Optional[str] = target_soft_id
        self.targetDbId: int = target_db_id


    @staticmethod
    def fetch_gloss_entry_links(connection : DbConnection, sense_id : int) -> dict[int, GlossLink]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_links = f"""
    SELECT r.id, e.human_key, e.id as entry_id
    FROM {DbConnectionInfo.schema}.sense_entry_relations r
    JOIN {DbConnectionInfo.schema}.sense_entry_rel_types rt on r.type_id = rt.id
    JOIN {DbConnectionInfo.schema}.entries e on r.entry_id = e.id
    WHERE rt.name = 'hasGlossLink' and (NOT e.hidden or e.reason_for_hiding='not-public') and r.sense_id={sense_id}
    """
        cursor.execute(sql_links)
        gloss_links = cursor.fetchall()
        if not gloss_links:
            return{}
        result = {}
        for db_row in gloss_links:
            result[db_row['id']] = GlossLink(db_row['entry_id'], db_row['human_key'])
        return result


    @staticmethod
    def fetch_gloss_sense_links(connection : DbConnection, sense_id : int) -> dict[int, GlossLink]:
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_links = f"""
    SELECT r.id, s.id as sense_id, s.order_no as sense_order, ps.order_no as parent_order, e.human_key
    FROM {DbConnectionInfo.schema}.sense_relations r
    JOIN {DbConnectionInfo.schema}.sense_rel_types rt on r.type_id = rt.id
    JOIN {DbConnectionInfo.schema}.senses s on r.sense_2_id = s.id
    LEFT JOIN {DbConnectionInfo.schema}.senses ps on s.parent_sense_id = ps.id
    JOIN {DbConnectionInfo.schema}.entries e on s.entry_id = e.id
    WHERE rt.name = 'hasGlossLink' and (NOT e.hidden or e.reason_for_hiding='not-public')
          and (NOT s.hidden or s.reason_for_hiding='not-public')
          and (ps.hidden is NULL or NOT ps.hidden or ps.reason_for_hiding='not-public')
          and r.sense_1_id={sense_id}
    """
        cursor.execute(sql_links)
        gloss_links = cursor.fetchall()
        if not gloss_links:
            return {}
        result = {}
        for db_row in gloss_links:
            endpoint = db_row['human_key']
            if 'parent_order' in db_row and db_row['parent_order']:
                endpoint = endpoint + '/' + str(db_row['parent_order'])
            endpoint = endpoint + '/' + str(db_row['sense_order'])
            result[db_row['id']] = GlossLink(db_row['sense_id'], endpoint)
        return result



class ExternalRelation:
    def __init__(self, remote_id : str, desc, rel_type : Optional[str] = None, scope : Optional[str] = None):
        self.remoteId : str = remote_id
        self.desctiption : str = desc
        self.type : Optional[str] = rel_type
        self.scope : Optional[str] = scope


    @staticmethod
    def fetch_exteral_synset_eq_relations(connection : DbConnection, synset_id : int,
                                          rel_type : Optional[str] = None) -> list[ExternalRelation]:
        where_clause = ''
        if rel_type is not None:
            where_clause = f"and lt.name = '{rel_type}' "
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_synset_lexemes = f"""
    SELECT syn.id as synset_id, el.url as url, el.remote_id as remote_id, lt.name as type,
           lt.description as description
    FROM {DbConnectionInfo.schema}.synsets syn
    JOIN {DbConnectionInfo.schema}.synset_external_links el ON syn.id = el.synset_id
    JOIN {DbConnectionInfo.schema}.external_link_types lt ON el.link_type_id = lt.id
    WHERE syn.id = {synset_id} {where_clause}and el.data is null
    ORDER BY el.remote_id
    """
        cursor.execute(sql_synset_lexemes)
        rels = cursor.fetchall()
        result = []
        for db_row in rels:
            result.append(ExternalRelation(db_row['remote_id'], db_row['description'], db_row['type']))
        return result


    @staticmethod
    def fetch_exteral_synset_neq_relations(connection : DbConnection, synset_id : int,
                                           rel_type : Optional[str] = None) -> list[ExternalRelation]:
        where_clause = ''
        if rel_type is not None:
            where_clause = f"and lt.name = '{rel_type}' "
        cursor = connection.cursor(cursor_factory=DictCursor)
        sql_synset_lexemes = f"""
    SELECT syn.id as synset_id, el.url as url, el.remote_id as remote_id, lt.name as type,
           lt.description as description, el.data->'Relation' #>> '{{}}' as rel_scope
    FROM {DbConnectionInfo.schema}.synsets syn
    JOIN {DbConnectionInfo.schema}.synset_external_links el ON syn.id = el.synset_id
    JOIN {DbConnectionInfo.schema}.external_link_types lt ON el.link_type_id = lt.id
    WHERE syn.id = {synset_id} {where_clause}and el.data is not null
    ORDER BY el.remote_id
    """
        cursor.execute(sql_synset_lexemes)
        rels = cursor.fetchall()
        result = []
        for db_row in rels:
            result.append(ExternalRelation(db_row['remote_id'], db_row['description'], db_row['type'],
                                           db_row['rel_scope']))
        return result
