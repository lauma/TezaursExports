from typing import Optional, Generator, Iterable
import regex

from lv.ailab.tezaurs.dbobjects.entries import Entry
from lv.ailab.tezaurs.dbobjects.examples import Example
from lv.ailab.tezaurs.dbobjects.gram import GramInfo, Flags
from lv.ailab.tezaurs.dbobjects.lexemes import Lexeme
from lv.ailab.tezaurs.dbobjects.relations import NamedInternalRelation, GlossLink
from lv.ailab.tezaurs.dbobjects.senses import Synset, Sense
from lv.ailab.tezaurs.dbobjects.sources import DictSource
from lv.ailab.tezaurs.utils.dict.gloss_normalization import mandatory_normalization, full_cleanup
from lv.ailab.tezaurs.utils.dict.ili import IliMapping
from lv.ailab.tezaurs.utils.dict.morpho_constants import MorphoAttr, MorphoVal
from lv.ailab.tezaurs.utils.dict.pron_normalization import prettify_pronunciation, prettify_text_with_pronunciation
from lv.ailab.tezaurs.utils.xml.writer import XMLWriter


class TEIWriter(XMLWriter):
    def __init__(self, file, dict_version, whitelist=None, indent_chars="  ", newline_chars="\n"):
        super().__init__(file, indent_chars, newline_chars)
        self.whitelist = whitelist
        self.debug_entry_id = ''
        self.dict_version = dict_version


    def _do_smart_leaf_node(self, name : str, attrs : dict[str, str], content : str,
                            ge_links : Optional[dict[int, GlossLink]] = None,
                            gs_links : Optional[dict[int, GlossLink]] = None):
        self.gen.ignorableWhitespace(self.indent_chars * self.xml_depth)
        self.gen.startElement(name, attrs)
        self._do_content_with_mentions_glosslinks(content, ge_links, gs_links)
        self.gen.endElement(name)
        self.gen.ignorableWhitespace(self.newline_chars)


    def _do_content_with_mentions_glosslinks(self, content : str,
                                             ge_links : Optional[dict[int, GlossLink]] = None,
                                             gs_links : Optional[dict[int, GlossLink]] = None):
        # parts = regex.split('</?(?:em|i)>', content)
        underscore_count = len(regex.findall(r'(?<!\\)_', content))
        if underscore_count % 2 > 0:
            print(f'Odd number of _ in entry {self.debug_entry_id}, string {content}!\n')
        parts = regex.split(r'(?<!\\)_+', content)
        is_mentioned = False
        # if regex.search('^</?(?:em|i)>', content):
        if regex.search(r'^_+', content):
            parts.pop(0)
            is_mentioned = True
        for part in parts:
            if is_mentioned:
                self.gen.startElement('mentioned', {})
                self._do_content_with_glosslinks(part, ge_links, gs_links)
                self.gen.endElement('mentioned')
                is_mentioned = False
            else:
                self._do_content_with_glosslinks(part, ge_links, gs_links)
                is_mentioned = True


    def _do_content_with_glosslinks(self, content : str,
                                    ge_links : Optional[dict[int, GlossLink]] = None,
                                    gs_links : Optional[dict[int, GlossLink]] = None):
        if not ge_links and not gs_links:
            self.gen.characters(full_cleanup(content))
        else:
            content_left = content
            glosslink_regex = r'(.*?)\[((?:\p{L}\p{M}*)+)\]\{([sen]):(\d+)\}(.*)'
            match = regex.fullmatch(glosslink_regex, content_left)
            while match:
                self.gen.characters(match.group(1))
                word = match.group(2)
                content_left = match.group(5)
                link_type = match.group(3)
                link_id = int(match.group(4))
                link_ref = None
                if link_type == 'e':
                    if not ge_links.get(link_id):
                        print(
                            f'Invalid gloss link {link_type}:{link_id} in entry {self.debug_entry_id}'
                            + f' (available links {ge_links}).\n')
                    link_ref = ge_links[link_id].targetSoftId
                elif link_type == 's':
                    if not gs_links.get(link_id):
                        print(
                            f'Invalid gloss link {link_type}:{link_id} in entry {self.debug_entry_id}'
                            + f' (available links {gs_links}).\n')
                    link_ref = gs_links[link_id].targetSoftId
                else:
                    print(f'Empty gloss link {link_type}:{link_id} in entry {self.debug_entry_id}\n')
                if link_ref:
                    self.gen.startElement('ref',
                                          {'target': f'{self.dict_version}/{link_ref}', 'type': 'disambiguation'})
                    self.gen.characters(word)
                    self.gen.endElement('ref')
                else:
                    self.gen.characters(word)
                match = regex.fullmatch(glosslink_regex, content_left)
            self.gen.characters(content_left)


    def print_head(self, dictionary : str, title_long : str = 'Dictionary', title_short : str = None,
                   edition : str = 'TODO', editors : str = 'TODO',
                   entry_count : str = 'TODO', lexeme_count : str = 'TODO', sense_count : str = 'TODO',
                   year : str = 'TODO', month : str = 'TODO',
                   url : Optional[str] = None, dict_copyright : Optional[str] = None):
        self.start_document()
        self.start_node('TEI', {})
        self.start_node('fileDesc', {})

        self.start_node('titleStmt', {})
        full_title = title_long
        # 2024-09-26 vēlreiz ar N. vienojamies, ka šeit liekt tikai `title_long`.
        #if title_short:
        #    full_title = title_short + ' — ' + title_long
        self.do_simple_leaf_node('title', {}, full_title)

        if dictionary.endswith('_wordforms'):
            self.do_simple_leaf_node('title', {'type': 'sub'}, 'Appendix: Wordforms')

        #if dictionary == 'tezaurs' or dictionary == 'mlvv' or dictionary == 'llvv' or dictionary == 'ltg':
        if editors and not dictionary.endswith('_wordforms'):
            self.do_simple_leaf_node('editor', {}, editors)
        self.end_node('titleStmt')

        self.start_node('editionStmt', {})
        self.start_node('edition', {})
        self.do_simple_leaf_node('title', {}, edition)
        if dictionary == 'tezaurs_wordforms':
            self.do_simple_leaf_node('ptr', {'target': f'{self.dict_version}_tei.xml'})
        self.end_node('edition')
        self.end_node('editionStmt')

        if not dictionary.endswith('_wordforms'):
            self.start_node('extent', {})
            self.do_simple_leaf_node('measure', {'unit': 'entry', 'quantity': entry_count}, )
            self.do_simple_leaf_node('measure', {'unit': 'lexeme', 'quantity': lexeme_count}, )
            self.do_simple_leaf_node('measure', {'unit': 'sense', 'quantity': sense_count}, )
            self.end_node('extent')

        self.start_node('publicationStmt', {})
        self.do_simple_leaf_node('date', {}, f"{year}-{month:02}")
        if dictionary.startswith('tezaurs') or dictionary == 'llvv' or dictionary.startswith('ltg'):
            self.gen.ignorableWhitespace(self.indent_chars * self.xml_depth)
            self.gen.startElement('publisher', {})
            self.gen.startElement('ref', {'target': 'https://ailab.lv'})
            self.gen.characters('AI Lab')
            self.gen.endElement('ref')
            self.gen.characters(' at Institute of Mathematics and Computer Science, University of Latvia')
            self.gen.endElement('publisher')
            self.gen.ignorableWhitespace(self.newline_chars)

        if dictionary == 'mlvv' or dictionary == 'llvv':
            self.gen.ignorableWhitespace(self.indent_chars * self.xml_depth)
            self.gen.startElement('publisher', {})
            self.gen.startElement('ref', {'target': 'https://lavi.lu.lv/'})
            self.gen.characters('Latvian Language Institute, Faculty of Humanities, University of Latvia')
            self.gen.endElement('ref')
            self.gen.endElement('publisher')
            self.gen.ignorableWhitespace(self.newline_chars)

        if dictionary.startswith('ltg'):
            self.gen.ignorableWhitespace(self.indent_chars * self.xml_depth)
            self.gen.startElement('publisher', {})
            self.gen.startElement('ref', {'target': 'https://rta.lv/'})
            self.gen.characters('Rēzekne Academy of Rīga Technical University')
            self.gen.endElement('ref')
            self.gen.endElement('publisher')
            self.gen.ignorableWhitespace(self.newline_chars)

        if dictionary.startswith('tezaurs') or dictionary == 'mlvv' or dictionary == 'llvv' or dictionary.startswith('ltg'):
            self.start_node('availability', {'status': 'free'})

            if url is not None and (dictionary.startswith('tezaurs') or dictionary == 'mlvv' or dictionary == 'llvv' or dictionary.startswith('ltg')):
                self.do_simple_leaf_node('p', {}, dict_copyright)

            self.do_simple_leaf_node('licence', {'target': 'https://creativecommons.org/licenses/by-sa/4.0/'},
                                     'Creative Commons Attribution-ShareAlike 4.0 International License')
            self.end_node('availability')
        if url is not None and (dictionary.startswith('tezaurs') or dictionary == 'mlvv' or dictionary == 'llvv' or dictionary.startswith('ltg')):
            self.do_simple_leaf_node('ptr', {'target': url})
        self.end_node('publicationStmt')

        if dictionary == 'llvv':
            self.start_node('sourceDesc', {})
            self.start_node('biblStruct', {})
            self.start_node('monogr', {})
            self.do_simple_leaf_node('title', {}, 'Latviešu literārās valodas vārdnīca')
            self.do_simple_leaf_node('editor', {}, 'Laimdots Ceplītis')
            self.do_simple_leaf_node('title', {}, 'Latviešu literārās valodas vārdnīca')
            self.start_node('imprint', {})
            self.do_simple_leaf_node('publisher', {}, 'Izdevniecība "Zinātne"')
            self.do_simple_leaf_node('pubPlace', {}, 'Rīga')
            self.do_simple_leaf_node('date', {}, '1972-1996')
            self.end_node('imprint')
            self.end_node('monogr')
            self.end_node('biblStruct')
            self.end_node('sourceDesc')

        self.end_node('fileDesc')

        if dictionary.endswith('_wordforms'):
            self.start_node('standOff', {})
        else:
            self.start_node('body', {})


    def print_tail(self, dictionary : str):
        if dictionary.endswith('_wordforms'):
            self.end_node('standOff')
        else:
            self.end_node('body')
        self.end_node('TEI')
        self.end_document()


    def print_back_matter(self, dictionary : str, sources : Generator[DictSource]):
        self.start_node('back', {})
        self.start_node('listBibl', {})
        for source in sources:
            # FIXME būtu labi, ja te varētu gudrāk dalīt elementos.
            source_title = regex.sub('</?(?:em|i)>', '', source.title)
            if source.url and len(source.url) > 0:
                self.do_simple_leaf_node('bibl',
                                         {'id': source.abbreviation, 'url': source.url}, source_title)
            else:
                self.do_simple_leaf_node('bibl', {'id': source.abbreviation}, source_title)
        if not dictionary.endswith('_wordforms') and (dictionary.startswith('ltg') or dictionary.startswith('tezaurs')):
            self.do_simple_leaf_node('bibl', {'id': 'MORPHO', 'url': 'https://github.com/LUMII-AILab/Morphology/'},
                                     'Paikens P. et al. Morphological Analyzer and Synthesizer for Latvian. ' +
                                     'Institute of Mathematics and Computer Science, University of Latvia, 2005-2026.')
        self.end_node('listBibl')
        self.end_node('back')


    # TODO: sakārtot, lai drukā ar jauno leksēmu drukāšanas funkciju un visas leksēmas
    def print_entry(self, entry : Entry, ili_map : IliMapping = None):
        # if self.whitelist is not None and not self.whitelist.check(entry['mainLexeme']['lemma'], entry['hom_id']):
        if self.whitelist is not None and not self.whitelist.check(entry.headword, entry.homonym):
            return
        self.debug_entry_id = entry.dbId
        entry_id = f'{self.dict_version}/{entry.dbId}'
        entry_xml_attrs = {'id': entry_id, 'sortKey': entry.headword}
        main_lexeme = entry.lexemes[0]
        if entry.homonym > 0:
            entry_xml_attrs['n'] = str(entry.homonym)
        if entry.type == 'mwe' or entry.type == 'MWE':
            entry_xml_attrs['type'] = 'mwe'
        #elif main_lexeme.lemma and 'pos' in main_lexeme and 'Vārda daļa' in main_lexeme['pos'] or entry.type == 'wordPart':
        elif entry.type == 'wordPart':
            entry_xml_attrs['type'] = 'affix'  # FIXME
        #elif main_lexeme.lemma and 'pos' in main_lexeme and 'Saīsinājums' in main_lexeme['pos'] or 'paradigm' in main_lexeme and main_lexeme['paradigm']['id'] == 'abbr':
        elif (main_lexeme.gramInfo.paradigmName == 'abbr'
              or MorphoAttr.POS in main_lexeme.gramInfo.flags and main_lexeme.gramInfo.flags[MorphoAttr.POS] == MorphoVal.ABBR) :
            entry_xml_attrs['type'] = 'abbr'
        elif (main_lexeme.gramInfo.paradigmName == 'foreign'
                or MorphoAttr.POS in main_lexeme.gramInfo.flags
                   and main_lexeme.gramInfo.flags[MorphoAttr.POS] == MorphoVal.FOREIGN
                or MorphoAttr.RESIDUAL_TYPE in main_lexeme.gramInfo.flags
                   and main_lexeme.gramInfo.flags[MorphoAttr.RESIDUAL_TYPE] == MorphoVal.FOREIGN):
            entry_xml_attrs['type'] = 'foreign'
        else:
            entry_xml_attrs['type'] = 'main'
        if entry.hidden:
            entry_xml_attrs['rend'] = 'hidden'
        self.start_node('entry', entry_xml_attrs)
        # FIXME homonīmi
        # self.print_lexeme(entry['mainLexeme'], entry['headword'], True)
        is_first = True
        self.print_gram(entry.gram)
        for lexeme in entry.lexemes:
            self.print_lexeme(lexeme, f'{self.dict_version}/{entry.dbId}', entry.headword, entry.type, is_first)
            is_first = False
        for sense in entry.senses:
            self.print_sense(sense, f'{self.dict_version}/{entry.dbId}', ili_map)
        for example in entry.examples:
            self.print_example(example)
        if entry.etymology:
            self._do_smart_leaf_node('etym', {}, mandatory_normalization(entry.etymology))
        for deriv in entry.morphoDerivatives:
            self.print_morpho_deriv(deriv)
        if entry.sources:
            self.print_esl_sources(entry.sources)
        self.end_node('entry')


    def print_lexeme(self, lexeme : Lexeme, id_stub : str, headword : str,
                     entry_type : str, is_main : bool = False):
        lexeme_id = f'{id_stub}/{lexeme.dbId}'
        form_attrs = {}
        if is_main:
            form_attrs = {'id': lexeme_id, 'type': 'lemma'}
        else:
            form_attrs = {'id': lexeme_id, 'type': lexeme_type(lexeme.type, entry_type)}
        if lexeme.hidden:
            form_attrs['rend'] = 'hidden'
        self.start_node('form', form_attrs)

        # TODO vai šito vajag?
        if is_main and lexeme.lemma != headword:
            self.do_simple_leaf_node('form', {'type': 'headword'}, headword)
        self.do_simple_leaf_node('orth', {'type': 'lemma'}, lexeme.lemma)
        for pronun in lexeme.pronunciations:
            self.do_simple_leaf_node('pron', {}, prettify_pronunciation(pronun))

        self.print_gram(lexeme.gramInfo)

        if lexeme.sources:
            self.print_esl_sources(lexeme.sources)

        self.end_node('form')


    def print_gram(self, gram : GramInfo, wraper_elem_name : Optional[str] = None):
        #if not gram.flags and not gram.structuralRestrictions and \
        #        not gram.freeText and not gram.inflectionText:
        if gram.is_empty():
            return

        if wraper_elem_name:
            self.start_node(wraper_elem_name, {})

        self.start_node('gramGrp', {})

        # TODO: kā labāk - celms kā karogs vai paradigmas daļa?
        if gram.paradigmName:
            paradigm_text = gram.get_paradigm_text()
            self.do_simple_leaf_node('iType', {'type': 'computational', 'corresp': '#MORPHO'}, paradigm_text)
        elif gram.inflectionText:
            self.do_simple_leaf_node('iType', {}, prettify_text_with_pronunciation(gram.inflectionText))

        if gram.flags:
            self.print_flags(gram.flags)
        if gram.structuralRestrictions:
            self.print_struct_restr(gram.structuralRestrictions)
        if not gram.flags and not gram.structuralRestrictions and gram.freeText:
            self.do_simple_leaf_node('gram', {}, prettify_text_with_pronunciation(gram.freeText))

        self.end_node('gramGrp')
        if wraper_elem_name:
            self.end_node(wraper_elem_name)


    # TODO piesaistīt karoga anglisko nosaukumu
    def print_flags(self, flags : Flags, ignored_flags : Optional[set[str]] = None):
        if not flags:
            return
        if ignored_flags is None:
            ignored_flags = {}

        self.start_node('gramGrp', {'type': 'properties'})
        for key in sorted(flags.keys()):
            if not key in ignored_flags:
                if isinstance(flags[key], list):
                    for value in flags[key]:
                        self.do_simple_leaf_node('gram', {'type': key}, value)
                else:
                    self.do_simple_leaf_node('gram', {'type': key}, flags[key])
        self.end_node('gramGrp')


    # TODO piesaistīt ierobežojuma anglisko nosaukumu un varbūt arī biežuma?
    def print_struct_restr(self, struct_restr):
        if 'OR' in struct_restr:
            self.start_node('gramGrp', {'type': 'restrictionDisjunction'})
            for restr in struct_restr['OR']:
                self.print_struct_restr(restr)
            self.end_node('gramGrp')
        elif 'AND' in struct_restr:
            self.start_node('gramGrp', {'type': 'restrictionConjunction'})
            for restr in struct_restr['AND']:
                self.print_struct_restr(restr)
            self.end_node('gramGrp')
        else:
            # if 'Restriction' not in struct_restr:
            #    print ("SAAD" + self.debug_entry_id)
            gramGrp_params = {'type': struct_restr['Restriction']}
            if 'Frequency' in struct_restr:
                gramGrp_params['subtype'] = struct_restr['Frequency']
            self.start_node('gramGrp', gramGrp_params)  # TODO piesaistīt anglisko nosaukumu
            if 'Value' in struct_restr and 'Flags' in struct_restr['Value']:
                self.print_flags(struct_restr['Value']['Flags'])
            if 'Value' in struct_restr and 'LanguageMaterial' in struct_restr['Value']:
                for material in struct_restr['Value']['LanguageMaterial']:
                    self.do_simple_leaf_node('gram', {'type': 'languageMaterial'}, material)
            self.end_node('gramGrp')


    def print_sense(self, sense : Sense, id_stub, ili_map : IliMapping):
        sense_id = f'{id_stub}/{sense.orderNo}'
        sense_xml_attrs = {'id': sense_id, 'n': f'{sense.orderNo}'}
        if sense.hidden:
            sense_xml_attrs['rend'] = 'hidden'
        self.start_node('sense', sense_xml_attrs)

        self.print_gram(sense.gram)
        norm_gloss = mandatory_normalization(sense.gloss)
        self._do_smart_leaf_node('def', {}, norm_gloss, sense.glossToEntryLinks, sense.glossToSenseLinks)
        if sense.synset:
            self.print_synset_related(sense.synset, ili_map)
        for example in sense.examples:
            self.print_example(example)
        for deriv in sense.semanticDerivatives:
            self.print_sem_deriv(deriv)
        if sense.sources:
            self.print_esl_sources(sense.sources)
        for subsense in sense.subsenses:
            self.print_sense(subsense, sense_id, ili_map)

        self.end_node('sense')


    def print_example(self, example : Example):
        if not example.text:
            return
        cit_attr = {'type': 'example'}
        if example.hidden:
            cit_attr['rend'] = 'hidden'
        self.start_node('cit', cit_attr)

        if not example.tokenLocation:
            self.do_simple_leaf_node('quote', {}, example.text)
        else:
            self.gen.ignorableWhitespace(self.indent_chars * self.xml_depth)
            self.gen.startElement('quote', {})
            self.gen.characters(example.text[:example.tokenLocation+0])
            self.gen.startElement('anchor', {})
            self.gen.endElement('anchor')
            self.gen.characters(example.text[example.tokenLocation+0:])
            self.gen.endElement('quote')
            self.gen.ignorableWhitespace(self.newline_chars)

        if example.source:
            self.do_simple_leaf_node('bibl', {}, example.source)

        self.end_node('cit')


    def print_esl_sources(self, sources : Iterable[DictSource]):
        if not sources:
            return
        self.start_node('listBibl', {})
        for source in sources:
            if source.details:
                self.start_node('bibl', {'corresp': f"#{source.abbreviation}"})
                self.do_simple_leaf_node('biblScope', {}, source.details)
                self.end_node('bibl')
            else:
                self.do_simple_leaf_node('bibl', {'corresp': f"#{source.abbreviation}"})
        self.end_node('listBibl')


    def print_sem_deriv(self, sem_deriv : NamedInternalRelation):
        xr_attr = {'type': 'derivative', 'subtype': 'semantics'}
        if sem_deriv.hidden:
            xr_attr['rend'] = 'hidden'
        self.start_node('xr', xr_attr)
        self.do_simple_leaf_node('lbl', {'type': 'this'}, f'{sem_deriv.myRole}')
        self.do_simple_leaf_node('lbl', {'type': 'target'}, f'{sem_deriv.targetRole}')
        self.do_simple_leaf_node('ref', {'target': f'{self.dict_version}/{sem_deriv.targetSoftId}'})
        self.end_node('xr')


    def print_morpho_deriv(self, morpho_deriv : NamedInternalRelation):
        xr_attr = {'type': 'derivative', 'subtype': 'morphology'}
        if morpho_deriv.hidden:
            xr_attr['rend'] = 'hidden'
        self.start_node('xr', {'type': 'derivative', 'subtype': 'morphology'})
        self.do_simple_leaf_node('lbl', {'type': 'this'}, f'{morpho_deriv.myRole}')
        self.do_simple_leaf_node('lbl', {'type': 'target'}, f'{morpho_deriv.targetRole}')
        self.do_simple_leaf_node('ref', {'target': f'{self.dict_version}/{morpho_deriv.targetSoftId}'})
        self.print_gram(morpho_deriv.gramInfo, 'desc')
        self.end_node('xr')


    def print_synset_related(self, synset : Synset, ili_map : IliMapping):
        if synset.senses:
            self.start_node('xr', {'type': 'synset', 'id': f'{self.dict_version}/synset:{synset.dbId}'})
            for sense in synset.senses:
                # TODO use hard ids when those are fixed
                self.do_simple_leaf_node('ref', {'type': 'synsetMember', 'target': f'{self.dict_version}/{sense.calculatedHumanId}'})
            if len(synset.externalEqRelations) > 0:
                pnw_id = None
                for relation in synset.externalEqRelations:
                    if relation.type == 'pwn-3.0':
                        pnw_id = relation.remoteId
                    self.do_simple_leaf_node(
                        'ref', {'type': 'externalEqualent', 'subtype': relation.desctiption, 'target': relation.remoteId})

                if ili_map and pnw_id is not None:
                    ili = ili_map.get_mapping(pnw_id)
                    self.do_simple_leaf_node(
                        'ref', {'type': 'externalEqualent', 'subtype': 'Open Multilingual Wordnet', 'target': ili})
            for relation in synset.externalNeqRelations:
                scope = relation.scope
                if scope.startswith('eq_has_'):
                    scope = scope[7:8].capitalize() + scope[8:]
                self.do_simple_leaf_node(
                    'ref', {'type': f'external{scope}', 'subtype': relation.desctiption, 'target': relation.remoteId})
            self.end_node('xr')

        for relation in synset.relations:
            xr_attr = {'type': f'{relation.relationLabel}'}
            if relation.hidden:
                xr_attr['rend'] = 'hidden'
            self.start_node('xr', xr_attr)
            self.do_simple_leaf_node('lbl', {'type': 'this'}, f'{relation.myRole}')
            self.do_simple_leaf_node('lbl', {'type': 'target'}, f'{relation.targetRole}')
            self.do_simple_leaf_node('ref', {'target': f'{self.dict_version}/synset:{relation.targetDbId}'})
            self.end_node('xr')

        if synset.gradset:
            self.start_node('xr',
                            {'type': 'gradationSet', 'id': f'{self.dict_version}/gradset:{synset.gradset.dbId}'})
            for other_synset in synset.gradset.memberIds:
                self.do_simple_leaf_node('ref', {'target': f'{self.dict_version}/synset:{other_synset}'})
            self.end_node('xr')
            if synset.gradset.category:
                self.start_node('xr', {'type': 'gradationClass'})
                self.do_simple_leaf_node('ref', {'target': f'{self.dict_version}/synset:{synset.gradset.category}'})
                self.end_node('xr')


    def print_wordform_set_entry(self, entry_id_no, lexeme_id_no, lemma, flags, formlist_from_json):
        full_lexeme_id = f'{self.dict_version}/{entry_id_no}/{lexeme_id_no}'
        self.start_node('entry', {'type': 'supplemental'})
        self.start_node('form', {})
        self.do_simple_leaf_node('ref', {'target': full_lexeme_id}, )
        self.do_simple_leaf_node('orth', {'type': 'lemma'}, lemma)
        self.print_flags(flags)
        for wordform in formlist_from_json:
            self.print_single_wordform(wordform)
        self.end_node('form')
        self.end_node('entry')


    def print_single_wordform(self, wordform_from_json):
        if 'Sistemātisks atvasinājums' in wordform_from_json and wordform_from_json['Sistemātisks atvasinājums'] == 'Jā':
            self.start_node('form', {'type': 'derivative'})
        else:
            self.start_node('form', {'type': 'inflection'})
        self.do_simple_leaf_node('orth', {}, wordform_from_json['Vārds'])
        self.print_flags(wordform_from_json, {'Vārds', 'Sistemātisks atvasinājums'})
        self.end_node('form')



def lexeme_type(type_from_db : str, entry_type : str) -> Optional[str]:
    match type_from_db:
        case 'default':
            if entry_type == 'word':
                return 'simple'
            elif entry_type == 'mwe':
                return 'phrase'
            else:
                return 'affix'
        case 'derivative':
            return 'derivative'
        case 'alternativeSpelling':
            return 'variant'
        case 'findVia':
            return 'other'
        case 'abbreviation':
            return 'abbreviation'
        case 'alternativeSpellingDerivative':
            return 'variantDerivative'
    return None

