from io import TextIOWrapper

from lv.ailab.tezaurs.dbobjects.lexemes import Lexeme
from lv.ailab.tezaurs.dbobjects.senses import Synset, Sense
from lv.ailab.tezaurs.utils.dict.gloss_normalization import full_cleanup
from lv.ailab.tezaurs.utils.dict.ili import IliMapping
from lv.ailab.tezaurs.utils.xml.writer import XMLWriter

# TODO future-work
# Jāpārtaisa LMF drukāšana tā, lai tēzaura nozīmes, kas atbilst vairākām
# leksēmām, tiktu dublētas katrai leksēmai ar savu atšķirīgu idu (varbūt
# elementa Sense id atribūtā jālieto nevis šķirkļa HK, bet leksēma). Tas
# tālāk rada nepieciešamību pārdomāt, kā pareizi veidot SenseRelation
# target atribūtu, jo tas vairs neizriet vienkārši no nozīmes datubāzes
# ida. Tāpat tas ietekmēs arī Synset elementā uzskaitītos members (jāzina,
# cik un kādus dublikātus uzskaitīt).

class LMFWriter(XMLWriter):
    def __init__(self, file : TextIOWrapper, dict_version : str, wordnet_id : str):
        super().__init__(file, "  ", "\n")
        self.debug_id : str = ""
        self.wordnet_id : str = wordnet_id
        self.dict_version : str = dict_version


    def print_head(self, wordnet_vers : str) -> None:
        self.start_document('<!DOCTYPE LexicalResource SYSTEM "http://globalwordnet.github.io/schemas/WN-LMF-1.1.dtd">')
        self.start_node_with_ws('LexicalResource', {'xmlns:dc': "http://purl.org/dc/elements/1.1/"})
        self.start_node_with_ws('Lexicon', {'id': self.wordnet_id,
                                    'label': 'Latvian Wordnet',
                                    'language': 'lv',
                                    'email': 'laura@ailab.lv',
                                    'license': 'https://creativecommons.org/licenses/by-sa/4.0/',
                                    'version': wordnet_vers,
                                    'url': 'https://wordnet.ailab.lv/',
                                    'citation': 'Peteris Paikens, Agute Klints, Ilze Lokmane, Lauma Pretkalniņa, Laura '
                                                + 'Rituma, Madara Stāde and Laine Strankale. Latvian WordNet. '
                                                + 'Proceedings of Global Wordnet Conference, 2023. DOI: 10.18653/v1/2023.gwc-1.23',
                                    'logo': 'https://wordnet.ailab.lv/images/mazais-logo-ailab.svg'})


    def print_tail(self) -> None:
        self.end_node_with_ws('Lexicon')
        self.end_node_with_ws('LexicalResource')
        self.end_document()


    def print_lexeme(self, lexeme : Lexeme, synseted_senses : list[Sense], print_tags : bool) -> None:
        gen_id = f'{self.wordnet_id}-{self.dict_version}'
        item_id = f'{gen_id}-{lexeme.parentEntryHK}-{lexeme.dbId}'
        self.debug_id = item_id
        self.start_node_with_ws('LexicalEntry', {'id': item_id})
        pos, abbr_pos = lexeme.gramInfo.get_poses()
        lmfpos = LMFWriter.lmfiy_pos(pos, abbr_pos, lexeme.lemma)
        lemma_params = {'writtenForm': lexeme.lemma, 'partOfSpeech': lmfpos}
        self.do_simple_leaf_node('Lemma', lemma_params)
        if print_tags:
            paradigm_text = lexeme.gramInfo.get_paradigm_text()
            if paradigm_text:
                self.do_simple_leaf_node('Tag', {}, paradigm_text)
        for syn_sense in synseted_senses:
            xml_attrs = {'id': f'{gen_id}-{lexeme.parentEntryHK}-{syn_sense.dbId}',
                                               'synset': f'{gen_id}-{syn_sense.synset.dbId}'}
            if not syn_sense.semanticDerivatives:
                self.do_simple_leaf_node('Sense', xml_attrs)
            else:
                self.start_node_with_ws('Sense', xml_attrs)
                for deriv in syn_sense.semanticDerivatives:
                    self.do_simple_leaf_node('SenseRelation',
                         {'relType' : 'derivation', 'target': f'{gen_id}-{deriv.targetEntryHk}-{deriv.targetDbId}'})
                self.end_node_with_ws('Sense')
        self.end_node_with_ws('LexicalEntry')


    def print_synset(self, synset : Synset, synset_lexemes : list[Lexeme], ili_map : IliMapping) -> None:
        item_id = f'{self.wordnet_id}-{self.dict_version}-{synset.dbId}'
        self.debug_id = item_id
        memberstr = ''
        for lexeme in synset_lexemes:
            memberstr = f'{memberstr} {self.wordnet_id}-{self.dict_version}-{lexeme.parentEntryHK}-{lexeme.dbId}'
        pnw_id = None

        if len(synset.externalEqRelations) > 1:
            print(f'Synset {synset.dbId} has more than 1 pwn-3.0 relation.')
        elif len(synset.externalEqRelations) == 1 and synset.externalEqRelations[0].remoteId:
            pnw_id = synset.externalEqRelations[0].remoteId
        ili = ili_map.get_mapping(pnw_id)

        self.start_node_with_ws('Synset', {'id': item_id, 'ili': ili, 'members': memberstr.strip()})
        unique_gloss = {}
        for sense in synset.senses:
            if sense.gloss:
                unique_gloss[full_cleanup(sense.gloss).lower()] = full_cleanup(sense.gloss)
        for gloss in unique_gloss:
            self.do_simple_leaf_node('Definition', {}, unique_gloss[gloss])
        for rel in synset.relations:
            self.do_simple_leaf_node('SynsetRelation',
                                     {'relType': rel.targetRole,
                                      'target': f'{self.wordnet_id}-{self.dict_version}-{rel.targetDbId}'})
        for sense in synset.senses:
            for example in sense.examples:
                attribs = {}
                if example.source:
                    attribs['source'] = example.source
                self.do_simple_leaf_node('Example', attribs, example.text)
        self.end_node_with_ws('Synset')


    @staticmethod
    def lmfiy_pos(pos: str, abbr_type: str, lemma : str) -> str:
        if not pos:
            return 'u'
        elif pos == 'Lietvārds' \
                or pos == 'Saīsinājums' and (abbr_type == 'Sugasvārds' or abbr_type == 'Īpašvārds'):
            return 'n'
        elif pos == 'Darbības vārds' or pos == 'Divdabis' \
                or pos == 'Saīsinājums' and abbr_type == 'Verbāls':
            return 'v'
        elif pos == 'Īpašības vārds' \
                or pos == 'Saīsinājums' and abbr_type == 'Īpašības vārds':
            return 'a'
        elif pos == 'Apstākļa vārds' \
                or pos == 'Saīsinājums' and abbr_type == 'Apstāklis':
            return 'r'
        elif pos == 'Prievārds':
            return 'p'
        elif pos == 'Partikula' or pos == 'Saiklis' or pos == 'Izsauksmes vārds' \
                or pos == 'Vietniekvārds' or pos == 'Skaitļa vārds':
            return 'x'
        elif pos == 'Reziduālis':
            return 'u'
        else:
            print(f'Unknown POS {pos} for lemma {lemma}.')
            return 'u'
