#!/usr/bin/env python3
import json
import sys
import warnings

from lv.ailab.tezaurs.dbaccess.connection import db_connect, get_dict_version, DbConnection
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.entries import Entry
from lv.ailab.tezaurs.dbobjects.gram import combine_inherited_flags
from lv.ailab.tezaurs.dbobjects.paradigms import Paradigm
from lv.ailab.tezaurs.exports.tei.tei_output import TEIWriter
from lv.ailab.tezaurs.exports.wordforms.json_wordform_utils import WordformReader


warn_multiple_inflsets : bool = True
skip_multiple_inflsets : bool = False
# Šobrīd vairāki locījumu komplekti ir tikai gadījumos, kad saīsinājumu kļūdaini sadala divās
# tekstvienībās, tāpēc labāk ir tos visus izlaist. Šis jāmaina, kad salabos saīsinājumus.

# DB connection is only needed for general dictionary info and paradigm flags, all the rest comes from JSON files.
connection : DbConnection
dbname : str = ''
dict_version : str
paradigms : dict [str, Paradigm]
wordform_list_path : str = "inflections.jsonl"

if len(sys.argv) > 1:
    dbname = sys.argv[1]
if dbname:
    DbConnectionInfo.dbname = dbname
else:
    dbname = DbConnectionInfo.dbname

if len(sys.argv) > 2:
    wordform_list_path = sys.argv[2]
wordform_source :WordformReader = WordformReader(wordform_list_path, False)

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

    entry_id_hk_map = Entry.fetch_all_entry_hk(connection)
    print("Entry mapping loaded!")

    counter = 0
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
            entry_hk = entry_id_hk_map.get(infl_json['entry_id'])
            if entry_hk:
                tei_printer.print_wordform_set_entry(
                    infl_json['entry_id'], entry_hk, infl_json['lexeme_id'], infl_json['lemma'], flags, infl_set)
        counter = counter + 1
        if counter % 1000 == 0:
            print (f'lexemes: {counter}')
    print (f'All {counter} lexemes done!')
    tei_printer.print_tail(f"{dict_version_data['dictionary']}_wordforms", [])

print(f'Done! Output written to {filename}')
wordform_source.print_bad_line_log()
