#!/usr/bin/env python3
import sys
from typing import Optional

from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.entries import Entry
from lv.ailab.tezaurs.dbobjects.sources import DictSource
from lv.ailab.tezaurs.utils.dict.ili import IliMapping
from lv.ailab.tezaurs.dbaccess.connection import db_connect, get_dict_version, DbConnection
from lv.ailab.tezaurs.exports.tei.tei_output import TEIWriter
from lv.ailab.tezaurs.exports.tei.whitelist import EntryWhitelist


# Major TODOs:
# - export MWE links
# - homonym grouping
# - migrate to hard sense IDs

connection : DbConnection
dbname : str = ''
dict_version : str
whitelist : Optional[EntryWhitelist] = None

omit_wordparts : bool = False
omit_pot_wordparts : bool = False
omit_mwe : bool = False

do_free_texts : bool = False
do_inflection_texts : bool = False
do_entrylevel_exmples : bool = False


if len(sys.argv) > 1:
    dbname = sys.argv[1]
if dbname:
    DbConnectionInfo.dbname = dbname
else:
    dbname = DbConnectionInfo.dbname

if len(sys.argv) > 2:
    whitelist = EntryWhitelist()
    whitelist.load(sys.argv[2])
    if len(whitelist.entries) < 1:
        whitelist = None
filename_infix = ""
if whitelist is not None:
    filename_infix = "_filtered"

connection = db_connect()
dict_version_data = get_dict_version(connection)
dict_version = dict_version_data['tag']
filename = f'{dict_version}_tei{filename_infix}.xml'
with open(filename, 'w', encoding='utf8') as out:
    ili_map = IliMapping()
    tei_printer = TEIWriter(out, dict_version, whitelist)
    tei_printer.print_head(
        dict_version_data['dictionary'], dict_version_data ['title_long'], dict_version_data ['title_short'],
        dict_version_data['release_name_en'], dict_version_data['editors_en'],
        dict_version_data['entries'], dict_version_data['lexemes'], dict_version_data['senses'],
        dict_version_data['year'], dict_version_data['month'],
        dict_version_data['url'], dict_version_data['copyright_en'])
    try:
        for entry in Entry.fetch_all_entries(connection, omit_mwe, omit_wordparts, omit_pot_wordparts, do_entrylevel_exmples):
            tei_printer.print_entry(entry, ili_map)
    except BaseException as err:
        print(f"Entry was: {tei_printer.debugEntry}")
        raise
    tei_printer.print_tail(dict_version_data['dictionary'], DictSource.fetch_all_sources(connection))
print(f'Done! Output written to {filename}')
