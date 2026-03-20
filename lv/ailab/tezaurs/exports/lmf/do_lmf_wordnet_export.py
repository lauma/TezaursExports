#!/usr/bin/env python3
import sys

from lv.ailab.tezaurs.dbaccess.connection import db_connect, get_dict_version
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.lexemes import Lexeme
from lv.ailab.tezaurs.dbobjects.senses import Synset, Sense
from lv.ailab.tezaurs.utils.dict.ili import IliMapping
from lv.ailab.tezaurs.exports.lmf.lmf_output import LMFWriter

# TODO: izrunas, LMF POS no tēzaura vārdšķiras
wordnet_id = 'wordnet_lv'
wordnet_vers = '1.0'
connection = None
dbname = None
dict_version = None
print_tags = True

if len(sys.argv) > 1:
    dbname = sys.argv[1]
if dbname:
    DbConnectionInfo.dbname = dbname
else:
    dbname = DbConnectionInfo.dbname

ili = IliMapping()
connection = db_connect()
dict_version_data = get_dict_version(connection)
dict_version = dict_version_data['tag']
filename = f'{dict_version}_lmf.xml'
with open(filename, 'w', encoding='utf8') as f:
    lmf_printer = LMFWriter(f, dict_version, wordnet_id)
    lmf_printer.print_head(wordnet_vers)
    try:
        for lexeme in Lexeme.fetch_all_synseted_lexemes(connection):
            synset_senses = Sense.fetch_synseted_senses_by_lexeme(connection, lexeme.dbId)
            lmf_printer.print_lexeme(lexeme, synset_senses, print_tags)
    except BaseException as err:
        print(f"Lexeme was: {lmf_printer.debug_id}")
        raise
    try:
        for synset in Synset.fetch_all_synsets(connection, 'pwn-3.0'):
            synset_lexemes = Lexeme.fetch_synset_lexemes(connection, synset.dbId)
            # Drukās netukšos sinsetus, šobrīd tas nozīmē, ka vajag definīciju un leksēmu.
            if synset.senses and synset_lexemes:
                lmf_printer.print_synset(synset, synset_lexemes, ili)
    except BaseException as err:
        print(f"Synset was: {lmf_printer.debug_id}")
        raise
    lmf_printer.print_tail()
print(f'Done! Output written to {filename}')
