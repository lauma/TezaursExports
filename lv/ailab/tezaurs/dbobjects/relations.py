from typing import Optional
from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.connection import DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbobjects.gram import GramInfo


class NamedInternalRelation:
    def __init__(self, my_role, target_role, hidden, target_db_id, target_soft_id = None ):
        self.myRole : str = my_role
        self.targetRole : str = target_role
        self.targetSoftId : Optional[str] = target_soft_id
        self.targetDbId : int = target_db_id
        self.relationLabel : Optional[str] = None
        self.hidden : bool = hidden
        self.gramInfo : GramInfo = GramInfo()


    @staticmethod
    def fetch_morpho_derivs(connection : DbConnection, entry_id : int) -> list[NamedInternalRelation]:
        result = []
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_derivs_from = f"""
    SELECT er.id, ert.name, ert.name_inverse, e2.id as end_id, e2.human_key as end_human_key,
           er.data as data, er.hidden
    FROM {db_connection_info['schema']}.entry_relations er
    JOIN {db_connection_info['schema']}.entry_rel_types ert on type_id = ert.id
    JOIN {db_connection_info['schema']}.entries e2 on entry_2_id = e2.id
    WHERE entry_1_id = {entry_id} and ert.name = 'derivativeOf'
          and (NOT er.hidden or er.reason_for_hiding='not-public')
          and (NOT e2.hidden or e2.reason_for_hiding='not-public')
    """
        cursor.execute(sql_derivs_from)
        derivs_from = cursor.fetchall()
        for deriv in derivs_from:
            relation = NamedInternalRelation(deriv.name, deriv.name_inverse, deriv.hidden,
                                             deriv.end_id, deriv.end_human_key)
            relation.gramInfo = GramInfo.extract_gram(deriv)
            result.append(relation)

        sql_derivs_to = f"""
    SELECT er.id, ert.name, ert.name_inverse, e1.id as end_id, e1.human_key as end_human_key,
           er.data as data, er.hidden
    FROM {db_connection_info['schema']}.entry_relations er
    JOIN {db_connection_info['schema']}.entry_rel_types ert on type_id = ert.id
    JOIN {db_connection_info['schema']}.entries e1 on entry_1_id = e1.id
    WHERE entry_2_id = {entry_id} and ert.name = 'derivativeOf'
          and (NOT er.hidden or er.reason_for_hiding='not-public')
          and (NOT e1.hidden or e1.reason_for_hiding='not-public')
    """
        cursor.execute(sql_derivs_to)
        derivs_to = cursor.fetchall()
        for deriv in derivs_to:
            relation = NamedInternalRelation(deriv.name_inverse, deriv.name, deriv.hidden,
                                             deriv.end_id, deriv.end_human_key)
            # 2024-09-19 ar valodniekiem WN seminārā tiek runāts, ka loģiskāk ir formantu un celma informāciju redzēt pie
            # atvasinājuma, nevis atvasināmā.
            # gram_dict = extract_gram(deriv)
            # deriv_dict.update(gram_dict)
            result.append(relation)

        sorted_result = sorted(result,
                               key=lambda item: (not item.hidden, item.myRole, item.targetRole, item.targetSoftId))
        return sorted_result


    @staticmethod
    def fetch_semantic_derivs_by_sense(connection : DbConnection, sense_id : int) -> list[NamedInternalRelation]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        result = []

        sql_sem_derivs_1 = f"""
    SELECT sr.id, sr.hidden, s2.id as sense_id, s2.order_no as sense_no, s2p.order_no as parent_sense_no,
           e2.human_key as entry_hk, sr.data->'role_1' #>> '{{}}' as role1, sr.data->'role_2' #>> '{{}}' as role2
    FROM {db_connection_info['schema']}.sense_relations as sr
    JOIN {db_connection_info['schema']}.sense_rel_types as srl ON sr.type_id = srl.id
    JOIN {db_connection_info['schema']}.senses as s2 ON sr.sense_2_id = s2.id
    LEFT OUTER JOIN {db_connection_info['schema']}.senses s2p ON s2.parent_sense_id = s2p.id
    JOIN {db_connection_info['schema']}.entries e2 on s2.entry_id = e2.id
    WHERE sr.sense_1_id = {sense_id} and srl.relation_name = 'semanticRelation' 
          and (NOT sr.hidden or sr.reason_for_hiding='not-public')
          and (NOT s2.hidden or s2.reason_for_hiding='not-public')
          and (s2p.hidden is NULL or NOT s2p.hidden or s2p.reason_for_hiding='not-public')
          and (NOT e2.hidden or e2.reason_for_hiding='not-public')
    """
        cursor.execute(sql_sem_derivs_1)
        sem_derivs_1 = cursor.fetchall()
        for deriv in sem_derivs_1:
            target_soft_id = f'{deriv.entry_hk}/{deriv.parent_sense_no}/{deriv.sense_no}'\
                if deriv.parent_sense_no else f'{deriv.entry_hk}/{deriv.sense_no}'
            relation = NamedInternalRelation(deriv.role1, deriv.role2, deriv.hidden, deriv.sense_no, target_soft_id)
            result.append(relation)

        sql_sem_derivs_2 = f"""
    SELECT sr.id, sr.hidden, s1.id as sense_id, s1.order_no as sense_no, s1p.order_no as parent_sense_no,
           e1.human_key as entry_hk, sr.data->'role_1' #>> '{{}}' as role1, sr.data->'role_2' #>> '{{}}' as role2
    FROM {db_connection_info['schema']}.sense_relations as sr
    JOIN {db_connection_info['schema']}.sense_rel_types as srl ON sr.type_id = srl.id
    JOIN {db_connection_info['schema']}.senses as s1 ON sr.sense_1_id = s1.id
    LEFT OUTER JOIN {db_connection_info['schema']}.senses s1p ON s1.parent_sense_id = s1p.id
    JOIN {db_connection_info['schema']}.entries e1 on s1.entry_id = e1.id
    WHERE sr.sense_2_id = {sense_id} and srl.relation_name = 'semanticRelation'
          and (NOT sr.hidden or sr.reason_for_hiding='not-public')
          and (NOT s1.hidden or s1.reason_for_hiding='not-public')
          and (s1p.hidden is NULL or NOT s1p.hidden or s1p.reason_for_hiding='not-public')
          and (NOT e1.hidden or e1.reason_for_hiding='not-public')
    """
        cursor.execute(sql_sem_derivs_2)
        sem_derivs_2 = cursor.fetchall()
        for deriv in sem_derivs_2:
            target_soft_id = f'{deriv.entry_hk}/{deriv.parent_sense_no}/{deriv.sense_no}'\
                if deriv.parent_sense_no else f'{deriv.entry_hk}/{deriv.sense_no}'
            relation = NamedInternalRelation(deriv.role2, deriv.role1, deriv.hidden, deriv.sense_no, target_soft_id)
            result.append(relation)

        sorted_result = sorted(result,
                               key=lambda item: (not item.hidden, item.myRole, item.targetRole, item.targetSoftId))
        return sorted_result


    @staticmethod
    def fetch_synset_relations(connection : DbConnection, synset_id : int) -> list[NamedInternalRelation]:
        result = []

        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_synset_rels_1 = f"""
    SELECT rel.id, rel.synset_1_id as other, rel.hidden, tp.name, tp.name_inverse, tp.relation_name as rel_name
    FROM {db_connection_info['schema']}.synset_relations rel
    JOIN {db_connection_info['schema']}.synset_rel_types tp ON rel.type_id = tp.id
    JOIN dict.senses s ON rel.synset_1_id = s.synset_id
    WHERE rel.synset_2_id = {synset_id}
          and (NOT rel.hidden or rel.reason_for_hiding='not-public')
          and (NOT s.hidden or s.reason_for_hiding='not-public')
    GROUP BY rel.id, tp.name_inverse, tp.name, rel_name
    """
        cursor.execute(sql_synset_rels_1)
        rel_members = cursor.fetchall()
        if rel_members:
            for member in rel_members:
                relation = NamedInternalRelation(member.name_inverse, member.name, member.hidden, member.other)
                relation.relationLabel = member.rel_name
                result.append(relation)

        sql_synset_rels_2 = f"""
    SELECT rel.id, rel.synset_2_id as other, rel.hidden, tp.name, tp.name_inverse, tp.relation_name as rel_name
    FROM {db_connection_info['schema']}.synset_relations rel
    JOIN {db_connection_info['schema']}.synset_rel_types tp ON rel.type_id = tp.id
    JOIN dict.senses s ON rel.synset_2_id = s.synset_id
    WHERE rel.synset_1_id = {synset_id}
          and (NOT rel.hidden or rel.reason_for_hiding='not-public')
          and (NOT s.hidden or s.reason_for_hiding='not-public')
    GROUP BY rel.id, tp.name, tp.name_inverse, rel_name
    """

        cursor.execute(sql_synset_rels_2)
        rel_members = cursor.fetchall()
        if rel_members:
            for member in rel_members:
                relation = NamedInternalRelation(member.name, member.name_inverse, member.hidden,
                                                 member.other)
                relation.relationLabel = member.rel_name
                result.append(relation)

        sorted_result = sorted(result,
                               key=lambda item: (not item.hidden, item.myRole, item.targetRole, item.targetDbId))
        return sorted_result



class GlossLink:
    def __init__(self, target_db_id, target_soft_id = None):
        self.targetSoftId: Optional[str] = target_soft_id
        self.targetDbId: int = target_db_id


    @staticmethod
    def fetch_gloss_entry_links(connection : DbConnection, sense_id : int) -> dict[int, GlossLink]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_links = f"""
    SELECT r.id, e.human_key, e.id as entry_id
    FROM {db_connection_info['schema']}.sense_entry_relations r
    JOIN {db_connection_info['schema']}.sense_entry_rel_types rt on r.type_id = rt.id
    JOIN {db_connection_info['schema']}.entries e on r.entry_id = e.id
    WHERE rt.name = 'hasGlossLink' and (NOT e.hidden or e.reason_for_hiding='not-public') and r.sense_id={sense_id}
    """
        cursor.execute(sql_links)
        gloss_links = cursor.fetchall()
        if not gloss_links:
            return{}
        result = {}
        for gloss_link in gloss_links:
            result[gloss_link.id] = GlossLink(gloss_link.entry_id, gloss_link.human_key)
            #result[gloss_link.id] = gloss_link.human_key
        return result


    @staticmethod
    def fetch_gloss_sense_links(connection : DbConnection, sense_id : int) -> dict[int, GlossLink]:
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_links = f"""
    SELECT r.id, s.id as sense_id, s.order_no as sense_order, ps.order_no as parent_order, e.human_key
    FROM {db_connection_info['schema']}.sense_relations r
    JOIN {db_connection_info['schema']}.sense_rel_types rt on r.type_id = rt.id
    JOIN {db_connection_info['schema']}.senses s on r.sense_2_id = s.id
    LEFT JOIN {db_connection_info['schema']}.senses ps on s.parent_sense_id = ps.id
    JOIN {db_connection_info['schema']}.entries e on s.entry_id = e.id
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
        for gloss_link in gloss_links:
            endpoint = gloss_link.human_key
            if gloss_link.parent_order and gloss_link.parent_order is not None:
                endpoint = endpoint + '/' + str(gloss_link.parent_order)
            endpoint = endpoint + '/' + str(gloss_link.sense_order)
            result[gloss_link.id] = GlossLink(gloss_link.sense_id, endpoint)
        return result



class ExternalRelation:
    def __init__(self, remote_id, desc, type = None, scope = None):
        self.remoteId : str = remote_id
        self.desctiption : str = desc
        self.type : Optional[str] = type
        self.scope : Optional[str] = scope


    @staticmethod
    def fetch_exteral_synset_eq_relations(connection : DbConnection, synset_id : int,
                                          rel_type : Optional[str] = None) -> list[ExternalRelation]:
        where_clause = ''
        if rel_type is not None:
            where_clause = f"and lt.name = '{rel_type}' "
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_synset_lexemes = f"""
    SELECT syn.id as synset_id, el.url as url, el.remote_id as remote_id, lt.name as type,
           lt.description as description
    FROM {db_connection_info['schema']}.synsets syn
    JOIN {db_connection_info['schema']}.synset_external_links el ON syn.id = el.synset_id
    JOIN {db_connection_info['schema']}.external_link_types lt ON el.link_type_id = lt.id
    WHERE syn.id = {synset_id} {where_clause}and el.data is null
    ORDER BY el.remote_id
    """
        cursor.execute(sql_synset_lexemes)
        rels = cursor.fetchall()
        result = []
        for rel in rels:
            result.append(ExternalRelation(rel.remote_id, rel.description, rel.type))
        return result


    @staticmethod
    def fetch_exteral_synset_neq_relations(connection : DbConnection, synset_id : int,
                                           rel_type : Optional[str] = None) -> list[ExternalRelation]:
        where_clause = ''
        if rel_type is not None:
            where_clause = f"and lt.name = '{rel_type}' "
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        sql_synset_lexemes = f"""
    SELECT syn.id as synset_id, el.url as url, el.remote_id as remote_id, lt.name as type,
           lt.description as description, el.data->'Relation' #>> '{{}}' as rel_scope
    FROM {db_connection_info['schema']}.synsets syn
    JOIN {db_connection_info['schema']}.synset_external_links el ON syn.id = el.synset_id
    JOIN {db_connection_info['schema']}.external_link_types lt ON el.link_type_id = lt.id
    WHERE syn.id = {synset_id} {where_clause}and el.data is not null
    ORDER BY el.remote_id
    """
        cursor.execute(sql_synset_lexemes)
        rels = cursor.fetchall()
        result = []
        for rel in rels:
            result.append(ExternalRelation(rel.remote_id, rel.description, rel.type, rel.rel_scope))
        return result
