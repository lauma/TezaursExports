from psycopg2.extras import NamedTupleCursor

from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info


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
