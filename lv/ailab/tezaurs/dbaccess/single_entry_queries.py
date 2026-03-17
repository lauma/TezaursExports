from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbobjects.gram import GramInfo


def fetch_morpho_derivs(connection, entry_id):
    if not entry_id:
        return
    result = []
    cursor = connection.cursor(cursor_factory=NamedTupleCursor)
    sql_derivs_from = f"""
SELECT er.id, ert.name, ert.name_inverse, e2.human_key, er.data as data, er.hidden
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
        deriv_dict = {'my_role': deriv.name, 'target_role': deriv.name_inverse,
                      'target_softid': deriv.human_key, 'hidden': deriv.hidden}
        gram_dict = GramInfo.extract_gram(deriv)
        deriv_dict['gram'] = gram_dict
        result.append(deriv_dict)

    sql_derivs_to = f"""
SELECT er.id, ert.name, ert.name_inverse, e1.human_key, er.data as data, er.hidden
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
        deriv_dict = {'my_role': deriv.name_inverse, 'target_role': deriv.name,
                      'target_softid': deriv.human_key, 'hidden': deriv.hidden}
        # 2024-09-19 ar valodniekiem WN seminārā tiek runāts, ka loģiskāk ir formantu un celma informāciju redzēt pie
        # atvasinājuma, nevis atvasināmā.
        #gram_dict = extract_gram(deriv)
        #deriv_dict.update(gram_dict)
        result.append(deriv_dict)

    sorted_result = sorted(result, key=lambda item: (not item['hidden'], item['my_role'], item['target_role'], item['target_softid']))
    return sorted_result
