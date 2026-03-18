from typing import Optional

from lv.ailab.tezaurs.dbobjects.lexemes import Lexeme
from lv.ailab.tezaurs.dbobjects.wordforms import Wordform
from lv.ailab.tezaurs.utils.dict.morpho_constants import MorphoVal, MorphoAttr


class GFUtils:

    INDENT : str = '  '
    BIG_SEPARATOR : str = '_'
    DEFAULT_LET_VARIABLE : str = 'l'
    GF_NUMBER_SINGULAR : str = 'Sg'
    GF_NUMBER_PLURAL : str = 'Pl'
    GF_CASE_VOCATIVE : str = 'Voc'
    GF_GEND_MASCULINE : str = 'Masc'
    GF_GEND_FEMININE : str = 'Fem'

    DEFAULT_GF_POS : dict[str, str] = {
        MorphoVal.NOUN: "N",
        #TODO ... Other entries
    }

    @staticmethod
    def get_GF_pos(lexeme : Lexeme) -> str:
        lexeme_pos = lexeme.gramInfo.flags[MorphoAttr.POS]
        result = GFUtils.DEFAULT_GF_POS[lexeme_pos]
        if (lexeme_pos == MorphoVal.NOUN
                and lexeme.gramInfo.flags.get(MorphoAttr.NOUN_TYPE, "") == MorphoVal.PROPER_NOUN
                and lexeme.gramInfo.flags.get(MorphoAttr.PNOUN_TYPE, "") == MorphoVal.PLACE_NAME):
            result = 'LN'
        return result


    # TODO aizstāt šo ar tagset XML nolasīšanu
    @staticmethod
    def get_GF_gender(gender : str) -> Optional[str]:
        match gender:
            case MorphoVal.MASCULINE: return GFUtils.GF_GEND_MASCULINE
            case MorphoVal.FEMININE: return GFUtils.GF_GEND_FEMININE
            case _: return None


    @staticmethod
    def normalize_for_GF(paradigm : str) -> Optional[str]:
        if not paradigm: return None
        return paradigm.replace('-', GFUtils.BIG_SEPARATOR)


    @staticmethod
    def form_concrete_lex_expr(gf_tail : str, lemma : str, paradigm : str) -> str:
        gf_paradigm = GFUtils.normalize_for_GF(paradigm)
        return f'{gf_paradigm}_from{gf_tail} "{lemma}"'


    @staticmethod
    def form_synest_comment(synsets : set[str]|list[str]) -> Optional[str]:
        if not synsets or len(synsets) < 1:
            return None
        result = GFUtils.INDENT * 3
        result = f"{result} -- {', '.join(sorted(synsets))}"
        return result


    # gf_std_form_string is something like `bro.s ! Sg ! Voc` - something to add to include standard forms from paradigm
    # Result is something like `variants{ "brāl" ; bro.s ! Sg ! Voc }`
    @staticmethod
    def _form_variant_list(wordforms : list[Wordform], gf_std_form_string : str) -> Optional[str]:
        if not wordforms or len(wordforms) < 1:
            return None
        include_standard_forms = not Wordform.is_replacing_wordform_list(wordforms)
        result = " ; ".join(map(lambda wf: f"\"{wf.form}\"", wordforms))
        if include_standard_forms:
            result = f"{result} ; {gf_std_form_string}"
        if len(wordforms) > 1 or include_standard_forms:
            result = f"variants {{ {result} }}"
        return result


    # Result is something like `{ Sg => old_noun.s ! Sg ** variants{ "brāl" ; bro.s ! Sg ! Voc } ; Pl => old_noun.s ! Pl ** { Voc = "brāļi" } }`
    @staticmethod
    def _form_table_with_vocative_extension(sg_voc_wordforms : list[Wordform],
                                            pl_voc_wordforms : list[Wordform]) -> Optional[str]:
        if ((not sg_voc_wordforms or len(sg_voc_wordforms) < 1)
                and (not pl_voc_wordforms or len(pl_voc_wordforms) < 1)):
            return None

        result = f"{GFUtils.GF_NUMBER_SINGULAR} => {GFUtils.DEFAULT_LET_VARIABLE}.s ! {GFUtils.GF_NUMBER_SINGULAR}"
        sg_voc = GFUtils._form_variant_list(
            sg_voc_wordforms, f"{GFUtils.DEFAULT_LET_VARIABLE}.s ! {GFUtils.GF_NUMBER_SINGULAR} ! {GFUtils.GF_CASE_VOCATIVE}")
        if sg_voc:
            result = f"{result} ** {{ {GFUtils.GF_CASE_VOCATIVE} => {sg_voc} }}"
        result = f"{result} ; "
        result = f"{result}{GFUtils.GF_NUMBER_PLURAL} => {GFUtils.DEFAULT_LET_VARIABLE}.s ! {GFUtils.GF_NUMBER_PLURAL}"
        pl_voc = GFUtils._form_variant_list(
            pl_voc_wordforms, f"{GFUtils.DEFAULT_LET_VARIABLE}.s ! {GFUtils.GF_NUMBER_PLURAL} ! {GFUtils.GF_CASE_VOCATIVE}")
        if sg_voc and pl_voc:
            result = f"{result} ** {{ {GFUtils.GF_CASE_VOCATIVE} => {pl_voc} }}"
        if pl_voc:
            result = f"{result}{GFUtils.GF_NUMBER_PLURAL} => {GFUtils.GF_CASE_VOCATIVE} => {pl_voc}"
        return f"table {{ {result} }}"


    # Here we form something like this:
    # let bro = noun_2a_fromLemma "brālis" in {
    #   s = table { Sg => bro.s ! Sg ** variants{ "brāl" ; bro.s ! Sg ! Voc } ;
    #     Pl => bro.s ! Pl ** { Voc => "brāļi" } } ;
    #   gend = bro.gend } ;
    @staticmethod
    def form_N_with_vocative_extension(lexeme : Lexeme, paradigm_expr : str,
                                       gender : str = None) -> Optional[str]:
        if len(lexeme.wordforms) < 1:
            return None
        sg_voc_wfs, leftover_wordforms = Wordform.filter_wordform_list(
            lexeme.wordforms, {MorphoAttr.NUMBER: MorphoVal.SINGULAR, MorphoAttr.CASE: MorphoVal.VOCATIVE})
        pl_voc_wfs, leftover_wordforms = Wordform.filter_wordform_list(
            leftover_wordforms, {MorphoAttr.NUMBER: MorphoVal.PLURAL, MorphoAttr.CASE: MorphoVal.VOCATIVE})

        extended_gf_table = GFUtils._form_table_with_vocative_extension(sg_voc_wfs, pl_voc_wfs)

        if not extended_gf_table or leftover_wordforms and len(leftover_wordforms) > 0:
            print(f'Skipping {lexeme.lemma} because additional wordforms are not all vocatives!')
            return None
        gf_gend = gender if gender else f"{GFUtils.DEFAULT_LET_VARIABLE}.gend"
        return f"let {GFUtils.DEFAULT_LET_VARIABLE} = {paradigm_expr} in {{ s = {extended_gf_table} ; gend = {gf_gend} }}"


    @staticmethod
    def form_N_with_changed_gender(paradigm_expr : str, gender : str) -> str:
        return f"let {GFUtils.DEFAULT_LET_VARIABLE} = {paradigm_expr} in {{ s = {GFUtils.DEFAULT_LET_VARIABLE}.s ; gend = {gender} }}"


    @staticmethod
    # Result is something like `let l = noun_6b_fromNomPl "Cēsis" in { s = l.s ! Pl ; gend = l.gend ; num = Pl }`
    def _form_LN(paradigm_expr : str, number : str, gender : str = None) -> str:
        gf_gend = gender if gender else f"{GFUtils.DEFAULT_LET_VARIABLE}.gend"
        return f"let {GFUtils.DEFAULT_LET_VARIABLE} = {paradigm_expr} in {{ s = {GFUtils.DEFAULT_LET_VARIABLE}.s ! {number} ; gend = {gf_gend} ; num = {number} }}"


    @staticmethod
    def form_LN_plural(paradim_expr : str, gender : str = None) -> str:
        return GFUtils._form_LN(paradim_expr, GFUtils.GF_NUMBER_PLURAL, gender)


    @staticmethod
    def form_LN_singular(paradim_expr : str, gender : str = None) -> str:
        return GFUtils._form_LN(paradim_expr, GFUtils.GF_NUMBER_SINGULAR, gender)


class GFPrintItem:
    def __init__(self,
                 lemmas : set[str] = None,
                 ids : set[int] = None,
                 synsets : set[str] = None):
        self.lemmas : set[str] = set() if lemmas is None else lemmas
        self.ids : set[int] = set() if ids is None else ids
        self.synsets : set[str] = set() if synsets is None else synsets
