from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info


def fetch_gloss_entry_links(connection, sense_id):
    if not sense_id:
        return
    cursor = connection.cursor(cursor_factory=NamedTupleCursor)
    sql_links = f"""
SELECT r.id, e.human_key
FROM {db_connection_info['schema']}.sense_entry_relations r
JOIN {db_connection_info['schema']}.sense_entry_rel_types rt on r.type_id = rt.id
JOIN {db_connection_info['schema']}.entries e on r.entry_id = e.id
WHERE rt.name = 'hasGlossLink' and (NOT e.hidden or e.reason_for_hiding='not-public') and r.sense_id={sense_id}
"""
    cursor.execute(sql_links)
    gloss_links = cursor.fetchall()
    if not gloss_links:
        return
    result = {}
    for gloss_link in gloss_links:
        result[gloss_link.id] = gloss_link.human_key
    return result


def fetch_gloss_sense_links(connection, sense_id):
    if not sense_id:
        return
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
        return
    result = {}
    for gloss_link in gloss_links:
        endpoint = gloss_link.human_key
        if gloss_link.parent_order and gloss_link.parent_order is not None:
            endpoint = endpoint + '/' + str(gloss_link.parent_order)
        endpoint = endpoint + '/' + str(gloss_link.sense_order)
        result[gloss_link.id]= {'softid': endpoint, 'hardid': gloss_link.sense_id}
    return result


def fetch_semantic_derivs_by_sense(connection, sense_id):
    if not sense_id:
        return
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
        deriv_link_dict = {'target_hardid': deriv.sense_id, 'my_role': deriv.role1, 'target_role': deriv.role2, 'hidden': deriv.hidden}
        if deriv.parent_sense_no:
            deriv_link_dict['target_softid'] = f'{deriv.entry_hk}/{deriv.parent_sense_no}/{deriv.sense_no}'
        else:
            deriv_link_dict['target_softid'] = f'{deriv.entry_hk}/{deriv.sense_no}'
        result.append(deriv_link_dict)

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
        deriv_link_dict = {'target_hardid': deriv.sense_id, 'target_role': deriv.role1, 'my_role': deriv.role2, 'hidden': deriv.hidden}
        if deriv.parent_sense_no:
            deriv_link_dict['target_softid'] = f'{deriv.entry_hk}/{deriv.parent_sense_no}/{deriv.sense_no}'
        else:
            deriv_link_dict['target_softid'] = f'{deriv.entry_hk}/{deriv.sense_no}'
        result.append(deriv_link_dict)

    sorted_result = sorted(result,
            key=lambda item: (not item['hidden'], item['my_role'], item['target_role'], item['target_softid']))
    return sorted_result


def fetch_synseted_senses_by_lexeme(connection, lexeme_id):
    if not lexeme_id:
        return
    cursor = connection.cursor(cursor_factory=NamedTupleCursor)
    sql_senses = f"""
SELECT s.id as sense_id, s.synset_id
FROM {db_connection_info['schema']}.senses s
JOIN {db_connection_info['schema']}.lexemes l on s.entry_id = l.entry_id
WHERE l.id = {lexeme_id} AND s.synset_id<>0 AND (NOT s.hidden OR s.reason_for_hiding='not-public')
"""
    cursor.execute(sql_senses)
    senses = cursor.fetchall()
    if not senses:
        return
    result = []
    for s in senses:
        result.append({'sense_id': s.sense_id, 'synset_id': s.synset_id})
    return result
