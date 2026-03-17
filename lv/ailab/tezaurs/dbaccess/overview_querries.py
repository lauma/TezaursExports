from functools import reduce
from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbaccess.single_synset_queries import fetch_exteral_synset_eq_relations
from lv.ailab.tezaurs.dbaccess.subentry_queries import fetch_wordforms, fetch_synseted_senses_by_lexeme
from lv.ailab.tezaurs.dbobjects.gram import combine_inherited_flags, GramInfo


def get_dict_version(connection):
    cursor = connection.cursor(cursor_factory=NamedTupleCursor)
    sql_dict_properties = f"""
    SELECT title, extract(YEAR from release_timestamp) as year, extract(MONTH from release_timestamp) as month,
        info->'dictionary' #>> '{{}}' as dictionary, info->'tag' #>> '{{}}' as tag,
        info->'counts'->'entries' #>> '{{}}' as entries,
        info->'counts'->'lexemes' #>> '{{}}' as lexemes,
        info->'counts'->'senses' #>> '{{}}' as senses,
        info->'title_short' #>> '{{}}' as title_short,
        info->'title_en' #>> '{{}}' as title_long,
        info->'release_name_en' #>> '{{}}' as release_name_en,
        info->'editors_en' #>> '{{}}' as editors_en,
        info->'copyright_en' #>> '{{}}' as copyright_en,
        info->'canonical_url' #>> '{{}}' as url
    FROM {db_connection_info['schema']}.metadata
"""
    cursor.execute(sql_dict_properties)
    row = cursor.fetchone()
    return {
        'dictionary': row.dictionary,
        'title_short': row.title_short, 'title_long': row.title_long,
        'tag': row.tag,
        'release_name_en': row.release_name_en, 'editors_en': row.editors_en, 'copyright_en': row.copyright_en,
        'entries': row.entries, 'lexemes': row.lexemes, 'senses': row.senses,
        'year': row.year, 'month': row.month,
        'url': row.url}


def fetch_all_synseted_lexemes(connection):
    cursor = connection.cursor(cursor_factory=NamedTupleCursor)
    sql_synset_lexemes = f"""
SELECT l.id as id, l.entry_id as entry_id, l.lemma as lemma,
    l.data->'Gram'->'Flags'->>'Vārdšķira' as lex_pos,
    l.data->'Gram'->'Flags'->>'Saīsinājuma tips' as lex_abbr_type,
    p.data->>'Vārdšķira' as p_pos,
    p.data->>'Saīsinājuma tips' as p_abbr_type,
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
GROUP BY l.id, paradigm, p_pos, p_abbr_type, entry_hk
ORDER BY l.lemma ASC
"""
    cursor.execute(sql_synset_lexemes)
    counter = 0
    while True:
        rows = cursor.fetchmany(1000)
        if not rows:
            break
        for row in rows:
            counter = counter + 1
            result = {'id': row.id, 'entry': row.entry_hk, 'lemma': row.lemma, 'pos': row.p_pos,
                      'abbr_type': row.p_abbr_type}
            if hasattr(row, 'paradigm') and row.paradigm:
                gram = GramInfo()
                gram.set_paradigm_stems(row)
                result['gram'] = gram

            if row.lex_pos:
                result['pos'] = row.lex_pos
            if row.lex_abbr_type:
                result['abbr_type'] = row.lex_abbr_type
            yield result
        print(f'lexemes: {counter}\r')


def fetch_all_lexemes_with_paradigms_and_synsets(connection):
    cursor = connection.cursor(cursor_factory=NamedTupleCursor)
    sql_lexemes = f"""
SELECT l.id, l.lemma, p.human_key,
	CASE WHEN l.data->'Gram'->'Flags'->>'Vārdšķira' IS NULL
		THEN p.data->>'Vārdšķira'
		ELSE l.data->'Gram'->'Flags'->>'Vārdšķira'
	END AS true_pos,
	p.data->>'Vārdšķira' AS paradigm_pos,
	l.data->'Gram'->'Flags' as flags, p.data as paradigm_flags,
	stem1, stem2, stem3
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
            result = {'id': row.id, 'lemma': row.lemma, 'paradigm': row.human_key,
                      'pos': row.true_pos, 'changed_pos': row.true_pos != row.paradigm_pos,
                      'paradigm_flags': row.paradigm_flags,
                      'combined_flags': combine_inherited_flags(row.flags, row.paradigm_flags),
                      'stem1': row.stem1, 'stem2': row.stem2, 'stem3': row.stem3,
                      'wordforms': fetch_wordforms(connection, row.id)}
            synset_senses = fetch_synseted_senses_by_lexeme(connection, row.id)
            synset_ids = set(map(lambda a: a['synset_id'] if 'synset_id' in a else {},
                               synset_senses)) if synset_senses else {}
            external_synset_ids = set(map(lambda a: a['id'], reduce(
                lambda a, b: a + b,
                map(lambda a: fetch_exteral_synset_eq_relations(connection, a), synset_ids),
                [])))
            result['synsets'] = synset_ids
            result['external_synsets'] = external_synset_ids
            yield result
        print(f'lexemes: {counter}\r')

