from typing import Optional, Iterable
from psycopg2.extras import DictRow

from lv.ailab.tezaurs.dbaccess.connection import JsonData
from lv.ailab.tezaurs.utils.dict.morpho_constants import MorphoAttr


type Flags = dict[str, str|Iterable[str]]


def combine_inherited_flags(lexeme_flags : Flags, paradigm_flags : Flags,
                            omit_paradigm_flags : Iterable[str] = None) ->Flags:
    if omit_paradigm_flags is None:
        omit_paradigm_flags = {}
    result = {}
    # General flag/property processing
    if lexeme_flags:
        result = lexeme_flags
    # including flag inheritance from paradigms
    if paradigm_flags:
        for key in paradigm_flags.keys():
            if omit_paradigm_flags and key in omit_paradigm_flags:
                continue
            if key not in result or not result[key]:
                result[key] = paradigm_flags[key]
    return result



class GramInfo:
    def __init__(self):
        self.flags : Flags = {}
        self.paradigmFlags : Flags = {}
        self.structuralRestrictions : JsonData = {}
        self.inflectionText : Optional[str] = None
        self.freeText : Optional[str] = None

        self.paradigmName : Optional[str] = None
        self.stemInfinity: Optional[str] = None
        self.stemPresent: Optional[str] = None
        self.stemPast: Optional[str] = None


    def is_empty(self) -> bool:
        if (self.flags or self.paradigmFlags or self.structuralRestrictions
                or self.inflectionText or self.freeText
                or self.paradigmName or self.stemInfinity or self.stemPresent or self.stemPast):
            return False
        return True


    def set_paradigm_data(self, from_element : DictRow) -> None:
        if 'paradigm' in from_element and from_element['paradigm']:
            self.paradigmName = from_element['paradigm']
        if 'paradigm_data' in from_element and from_element['paradigm_data']:
            self.paradigmFlags = from_element['paradigm_data']
        if 'stem1' in from_element and from_element['stem1']:
            self.stemInfinity = from_element['stem1']
        if 'stem2' in from_element and from_element['stem2']:
            self.stemPresent = from_element['stem2']
        if 'stem3' in from_element and from_element['stem3']:
            self.stemPast = from_element['stem3']


    def get_paradigm_text(self) -> Optional[str]:
        if not self.paradigmName:
            return None

        result = self.paradigmName
        if self.stemInfinity or self.stemPresent or self.stemPast:
            result = result + ':'
            if self.stemInfinity:
                result = result + self.stemInfinity + ';'
            else:
                result = result + ';'
            if self.stemPresent:
                result = result + self.stemPresent + ';'
            else:
                result = result + ';'
            if self.stemPast:
                result = result + self.stemPast
        return result


    def get_poses(self) -> tuple[Optional[str], Optional[str]]:
        pos = self.flags.get(MorphoAttr.POS, None)
        abbr_pos = self.flags.get(MorphoAttr.ABBR_TYPE, None)
        return pos, abbr_pos


    def is_attr_overrided(self, attribute : str) -> bool:
        if not self.flags or not self.paradigmFlags:
            return False
        if attribute not in self.paradigmFlags or attribute not in self.flags:
            return False
        if self.flags[attribute] != self.paradigmFlags[attribute]:
            return True
        return False


    @staticmethod
    def extract_gram(element : DictRow, omit_flags : Optional[Iterable[str]] = None) -> GramInfo:
        if not omit_flags:
            omit_flags = {}
        result = GramInfo()
        # Kaut kāda huiņa, ka šis atgriež None, nevis {}:
        # element_data = element.get('data',{})
        element_data = element['data'] if 'data' in element else {}
        if element_data is None:
            element_data = {}

        # Paradigms
        result.set_paradigm_data(element)

        # General flag/property processing
        element_flags = element_data.get('Gram', {}).get('Flags', {})
        paradigm_flags = element['paradigm_data'] if 'paradigm_data' in element else {}
        if paradigm_flags is None:
            paradigm_flags = {}
        combined_flags = combine_inherited_flags(element_flags, paradigm_flags, omit_flags)
        if combined_flags:
            result.flags = combined_flags

        # Structural restrictions
        result.structuralRestrictions = element_data.get('Gram', {}).get('StructuralRestrictions', None)

        # Inflection text
        result.inflectionText = element_data.get('Gram', {}).get('Inflection', None)

        # Free text
        result.freeText = element_data.get('Gram', {}).get('FreeText', None)

        return result
