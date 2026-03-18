from psycopg2.extras import NamedTupleCursor
from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info

def fetch_synset_relations(connection, synset_id):
    if not synset_id:
        return
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
            result.append({'target_id': member.other, 'target_role': member.name,
                           'my_role': member.name_inverse, 'relation': member.rel_name, 'hidden': member.hidden})

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
            result.append({'target_id': member.other, 'target_role': member.name_inverse,
                           'my_role': member.name, 'relation': member.rel_name, 'hidden': member.hidden})

    sorted_result = sorted(result, key=lambda item: (not item['hidden'], item['my_role'], item['target_role'], item['target_id']))
    return sorted_result


def fetch_exteral_synset_eq_relations(connection, synset_id, rel_type=None):
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
        result.append({'id': rel.remote_id, 'desc': rel.description, 'type': rel.type})
    return result

def fetch_exteral_synset_neq_relations(connection, synset_id, rel_type=None):
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
        result.append({'id': rel.remote_id, 'desc': rel.description, 'type': rel.type, 'scope': rel.rel_scope})
    return result
