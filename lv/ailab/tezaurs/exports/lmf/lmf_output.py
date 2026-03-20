from lv.ailab.tezaurs.dbobjects.lexemes import Lexeme
from lv.ailab.tezaurs.dbobjects.senses import Synset, Sense
from lv.ailab.tezaurs.utils.dict.gloss_normalization import full_cleanup
from lv.ailab.tezaurs.utils.dict.ili import IliMapping
from lv.ailab.tezaurs.utils.xml.writer import XMLWriter


class LMFWriter(XMLWriter):

    def __init__(self, file, dict_version, wordnet_id):
        super().__init__(file, "  ", "\n")
        self.debug_id : str = ""
        self.wordnet_id : str = wordnet_id
        self.dict_version : str = dict_version

    def print_head(self, wordnet_vers : str):
        self.start_document('<!DOCTYPE LexicalResource SYSTEM "http://globalwordnet.github.io/schemas/WN-LMF-1.1.dtd">')
        self.start_node('LexicalResource', {'xmlns:dc': "http://purl.org/dc/elements/1.1/"})
        self.start_node('Lexicon', {'id': self.wordnet_id,
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

    def print_tail(self):
        self.end_node('Lexicon')
        self.end_node('LexicalResource')
        self.end_document()

    def print_lexeme(self, lexeme : Lexeme, synseted_senses : list[Sense], print_tags : bool):
        gen_id = f'{self.wordnet_id}-{self.dict_version}'
        item_id = f'{gen_id}-{lexeme.parentEntryHK}-{lexeme.dbId}'
        self.debug_id = item_id
        self.start_node('LexicalEntry', {'id': item_id})
        pos, abbr_pos = lexeme.gramInfo.get_poses()
        lmfpos = LMFWriter.lmfiy_pos(pos, abbr_pos, lexeme.lemma)
        lemma_params = {'writtenForm': lexeme.lemma, 'partOfSpeech': lmfpos}
        self.do_simple_leaf_node('Lemma', lemma_params)
        if print_tags:
            paradigm_text = lexeme.gramInfo.get_paradigm_text()
            if paradigm_text:
                self.do_simple_leaf_node('Tag', {}, paradigm_text)
        for syn_sense in synseted_senses:
            self.do_simple_leaf_node('Sense',
                     {'id': f'{gen_id}-{lexeme.parentEntryHK}-{syn_sense.dbId}',
                                               'synset': f'{gen_id}-{syn_sense.synset.dbId}'})
        self.end_node('LexicalEntry')


    def print_synset(self, synset : Synset, synset_lexemes : list[Lexeme], ili_map : IliMapping):
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

        self.start_node('Synset', {'id': item_id, 'ili': ili, 'members': memberstr.strip()})
        unique_gloss = {}
        for sense in synset.senses:
            if sense.gloss:
                unique_gloss[full_cleanup(sense.gloss)] = 1
        for gloss in unique_gloss:
            self.do_simple_leaf_node('Definition', {}, gloss)
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
        self.end_node('Synset')


    @staticmethod
    def lmfiy_pos(pos: str, abbr_type: str, lemma) -> str:
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
