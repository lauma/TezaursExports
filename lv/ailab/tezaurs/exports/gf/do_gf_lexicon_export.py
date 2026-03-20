#!/usr/bin/env python3
import sys

from lv.ailab.tezaurs.dbaccess.connection import db_connect, get_dict_version
from lv.ailab.tezaurs.dbaccess.db_config import DbConnectionInfo
from lv.ailab.tezaurs.dbobjects.lexemes import Lexeme
from lv.ailab.tezaurs.exports.gf.gf_output import GFConcreteWriter, GFAbstractWriter
from lv.ailab.tezaurs.exports.gf.gf_utils import GFUtils, GFPrintItem
from lv.ailab.tezaurs.utils.dict.morpho_constants import MorphoVal, MorphoAttr

connection = None
dbname = None
dict_version = None
implemented_paradigms = {
            "noun-1a", "noun-1b", "noun-2a", "noun-2b", "noun-2c", "noun-2d",
			"noun-3f", "noun-3m", "noun-4f", "noun-4m", "noun-5fa", "noun-5fb",
			"noun-5ma", "noun-5mb", "noun-6a", "noun-6b",
}

# Initialize DB
if len(sys.argv) > 1:
    dbname = sys.argv[1]
if dbname:
    DbConnectionInfo.dbname = dbname
else:
    dbname = DbConnectionInfo.dbname
connection = db_connect()
dict_version_data = get_dict_version(connection)
dict_version = dict_version_data['tag']
dict_lang = 'Ltg' if dict_version_data['dictionary'] == 'ltg' else 'Lav'

# Initialize both GF files (concrete and abstract), print their headers.
module_name_abs = f'PortedTezaursDict{dict_lang}Abs'
gf_abs_printer = GFAbstractWriter(f'{module_name_abs}.gf')
gf_abs_printer.print_head(module_name_abs, dict_version)
module_name_conc = f'PortedTezaursDict{dict_lang}'
gf_conc_printer = GFConcreteWriter(f'{module_name_conc}.gf')
gf_conc_printer.print_head(module_name_conc, module_name_abs, dict_version)

# To avoid duplicates in resulting GF, we first process all lexemes and store
# them in this map variable (indexed by resulting concrete grammar expression and GF
# category/POS). Only after all lexemes are processed, we do the writing in
# the GF output files.
result_lexemes_by_concrete : dict[tuple[str, str], GFPrintItem] = {}
for lexeme in Lexeme.fetch_all_lexemes_with_paradigms_and_synsets(connection):
    # Currently only noun processing. Must be updated for other POS, when structure becomes clearer.
    if lexeme.gramInfo.paradigmName not in implemented_paradigms:
        continue
    if lexeme.gramInfo.is_attr_overrided(MorphoAttr.POS):
        print(f'Skipping {lexeme.lemma} because of pos!')
        continue
    gf_pos = GFUtils.get_GF_pos(lexeme)
    # TODO: other POS
    # TODO for nouns:
    #  - better treatment for plurale tantum?
    #  - correct gender for "ļaudis"

    conc_expr = None
    gender = GFUtils.get_GF_gender(lexeme.gramInfo.flags[MorphoAttr.GENDER])\
        if lexeme.gramInfo.is_attr_overrided(MorphoAttr.GENDER) else None
    lemma_irregs = lexeme.gramInfo.flags.get(MorphoAttr.LEMMA_WEIRDNESS, [])

    if len(lemma_irregs) < 1 or len(lemma_irregs) == 1 and MorphoVal.SINGULAR in lemma_irregs:
        # Standart nouns
        conc_expr = GFUtils.form_concrete_lex_expr('Lemma', lexeme.lemma, lexeme.gramInfo.paradigmName)
        if gf_pos == 'LN':
            # Special processing for place names
            conc_expr = GFUtils.form_LN_singular(conc_expr, gender)
    elif len(lemma_irregs) == 1 and MorphoVal.PLURAL in lemma_irregs:
        # Standart nouns
        conc_expr = GFUtils.form_concrete_lex_expr('NomPl', lexeme.lemma, lexeme.gramInfo.paradigmName)
        if gf_pos == 'LN':
            # Special processing for place names
            conc_expr = GFUtils.form_LN_plural(conc_expr, gender)

    # Currently we don't know what to do with other lemma cases.
    else:
        print(f'Skipping {lexeme.lemma} because of lemma type {lemma_irregs}!')
        continue

    # Here we add custom vocatives
    if lexeme.wordforms:
        if gf_pos != "N":
            print(f'Skipping {lexeme.lemma} because don\'t know, how to add vocatives to {gf_pos} type!')
            continue
        voc_expr = GFUtils.form_N_with_vocative_extension(lexeme, conc_expr, gender)
        if not voc_expr:
            continue
        conc_expr = voc_expr
    elif gender and gf_pos != "LN":
        conc_expr = GFUtils.form_N_with_changed_gender(conc_expr, gender)

    # If we have actually managed to get a concrete expression, then we add it to the great data structure for printing
    if conc_expr:
        result_entry = GFPrintItem()
        if (conc_expr, gf_pos) in result_lexemes_by_concrete:
            result_entry = result_lexemes_by_concrete[(conc_expr, gf_pos)]
        result_entry.lemmas.add(lexeme.lemma)
        result_entry.ids.add(lexeme.dbId)
        result_entry.synsets.update(lexeme.externalSynsetIds)
        result_lexemes_by_concrete[(conc_expr, gf_pos)] = result_entry

# Finally we print all the processed lexemes to output...
sorting_funct = lambda x: sorted(result_lexemes_by_concrete[x].lemmas, key=lambda y : y.lower())[0].lower()
for (conc_expr, gf_pos) in sorted(result_lexemes_by_concrete.keys(), key=lambda x : (sorting_funct(x), x[1])):
    gf_lexeme_data = result_lexemes_by_concrete[(conc_expr, gf_pos)]
    lemma = sorted(gf_lexeme_data.lemmas, key=lambda y : y.lower())[0]
    variable_postfix = GFUtils.BIG_SEPARATOR.join(str(lex_id) for lex_id in sorted(gf_lexeme_data.ids))
    variable_postfix = f"{variable_postfix}{GFUtils.BIG_SEPARATOR}{gf_pos}"
    synset_comment = GFUtils.form_synest_comment(gf_lexeme_data.synsets)
    if len(gf_lexeme_data.lemmas) > 1:
        print(f"Warning: from lemma set {{ {'; '.join(gf_lexeme_data.lemmas)} }} picking \"{lemma}\"!\n")

    gf_abs_printer.print_lexeme(lemma, variable_postfix, gf_pos, synset_comment)
    gf_conc_printer.print_lexeme(lemma, variable_postfix, conc_expr, synset_comment)

# ... And finish the GF files with appropriate endings.
gf_abs_printer.print_tail()
gf_conc_printer.print_tail()
