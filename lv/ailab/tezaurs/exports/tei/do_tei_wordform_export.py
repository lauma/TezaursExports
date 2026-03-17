#!/usr/bin/env python3
from lv.ailab.tezaurs.dbaccess.connection import db_connect
from lv.ailab.tezaurs.dbaccess.db_config import db_connection_info
from lv.ailab.tezaurs.dbaccess.overview_querries import get_dict_version
from lv.ailab.tezaurs.dbobjects.gram import combine_inherited_flags
from lv.ailab.tezaurs.dbobjects.paradigms import Paradigm
from lv.ailab.tezaurs.exports.tei.tei_output import TEIWriter
from lv.ailab.tezaurs.exports.wordforms.json_wordform_utils import WordformReader
import json
import sys
import warnings

warn_multiple_inflsets = True
skip_multiple_inflsets = False
# Šobrīd vairāki locījumu komplekti ir tikai gadījumos, kad saīsinājumu kļūdaini sadala divās
# tekstvienībās, tāpēc labāk ir tos visus izlaist. Šis jāmaina, kad salabos saīsinājumus.

# DB connection is only needed for general dictionary info and paradigm flags, all the rest comes from JSON files.
connection = None
dbname = None
dict_version = None
paradigms = None
wordform_list_path = "inflections.jsonl"

if len(sys.argv) > 1:
    dbname = sys.argv[1]
if dbname:
    db_connection_info['dbname'] = dbname
else:
    dbname = db_connection_info['dbname']

if len(sys.argv) > 2:
    wordform_list_path = sys.argv[2]
wordform_source = WordformReader(wordform_list_path, False)

connection = db_connect()
dict_version_data = get_dict_version(connection)
dict_version = dict_version_data['tag']
paradigms = Paradigm.fetch_all_paradigms(connection)
filename = f'{dict_version}_wordforms_tei.xml'
with open(filename, 'w', encoding='utf8') as out:
    tei_printer = TEIWriter(out, dict_version, None, ' ')
    tei_printer.print_head(
        f"{dict_version_data['dictionary']}_wordforms", dict_version_data['title_long'], dict_version_data['title_short'],
        dict_version_data['release_name_en'], dict_version_data['editors_en'],
        dict_version_data['entries'], dict_version_data['lexemes'], dict_version_data['senses'],
        dict_version_data['year'], dict_version_data['month'],
        dict_version_data['url'], dict_version_data['copyright_en'])

    for infl_json in wordform_source.process_line_by_line():
        if not infl_json or len(infl_json) < 1:
            continue
        if warn_multiple_inflsets and len(infl_json['inflectedForms']) != 1:
            warnings.warn(
                "Following wordform JSON doesn't have exactly one set of inflections: " \
                    + json.dumps(infl_json, ensure_ascii=False))
        if skip_multiple_inflsets and len(infl_json['inflectedForms']) != 1:
            continue
        for infl_set in infl_json['inflectedForms']:
            lexeme_flags = {}
            if 'flags' in infl_json:
                lexeme_flags = infl_json['flags']
            flags = combine_inherited_flags(lexeme_flags, paradigms[infl_json['paradigm']].flags,
                                            {'Stems', 'Morfotabulas tips', 'Paradigmas īpatnības'})
            tei_printer.print_wordform_set_entry(
                infl_json['entry_id'], infl_json['lexeme_id'], infl_json['lemma'], flags, infl_set)

    tei_printer.print_tail(f"{dict_version_data['dictionary']}_wordforms")

print(f'Done! Output written to {filename}')
wordform_source.print_bad_line_log()
