import json
import regex
import warnings
from io import TextIOWrapper
from typing import Generator

from lv.ailab.tezaurs.dbaccess.connection import JsonData
from lv.ailab.tezaurs.dbobjects.gram import Flags


class IspellFilter:

    LEXEME_DISQUALIFYING_FLAGS : dict[str, list[str]] = {
        "Valodas normēšana": ["Nevēlams"],
        "Lietojums": ["Apvidvārds", "Barbarisms", "Bērnu valoda", "Dialektisms", "Īsziņās", "Lamuvārds", "Neaktuāls", "Neliterārs", "Nevēlams", "Novecojis", "Okazionālisms", "Sarunā ar bērniem", "Sarunvaloda", "Sens, reti lietots vārds", "Slengs", "Vulgārisms", "Žargonisms"],
        "Stils" : ["Vienkāršrunas stilistiskā nokrāsa"],
        "Dialekta iezīmes": [], # Empty list means any value disqualifies
        "Izlokšņu grupa": [],
        "Izloksne": [],
        "Vārdšķira" : ["Reziduālis", "Vārds svešvalodā"]
    }
    FORM_DISQUALIFYING_FLAGS : dict[str, list[str]] = {
        "Pakāpe": ["Pārākā", "Vispārākā"]
    }
    DISQUALIFYING_PARADIGMS : list[str] = ["foreign", "number", "punct", "residual"]


    @staticmethod
    def _flags_match_omit(flags: Flags, criteria : Flags) -> bool:
        if not flags:
            return False
        for flag_type in criteria:
            if flag_type in flags and flags[flag_type]:
                if len(criteria[flag_type]) < 1:
                    return True
                else:
                    for flag_value in criteria[flag_type]:
                        if flag_value in flags[flag_type] or flags[flag_type] == flag_value:
                            return True
        return False


    # Checks if at least one of the lexemes associated with the given inflection path
    # matches the criteria for being included in spellchecker output (not regional, rude, etc.)
    def lexeme_good_for_spelling(self, inflection_json : JsonData) -> bool:
        if inflection_json["paradigm"] in self.DISQUALIFYING_PARADIGMS:
            return False
        if "flags" in inflection_json:
            return not self._flags_match_omit(inflection_json["flags"], self.LEXEME_DISQUALIFYING_FLAGS)
        return True


    def form_good_for_spelling(self, form_property_map : Flags) -> bool:
        bad = self._flags_match_omit(form_property_map, self.FORM_DISQUALIFYING_FLAGS) \
               or self._flags_match_omit(form_property_map, self.LEXEME_DISQUALIFYING_FLAGS)
        return not bad



class WordformReader:
    def __init__(self, wordform_list_path : str, correct_fffd : bool = False):
        self.wordform_file : TextIOWrapper = open(wordform_list_path, 'r', encoding='utf8')
        self.correct_fffd : bool = correct_fffd

        self.bad_lines : list[str] = []
        self.skipped : int = 0

    def process_line_by_line(self) -> Generator[JsonData] :
        for line in self.wordform_file:
            if regex.search('\uFFFD', line):
                self.bad_lines.append(line)
                if self.correct_fffd:
                    line = line.replace('"V\uFFFD\uFFFDrds"', '"Vārds"')

                    line = line.replace('"Akuzat\uFFFD\uFFFDvs"', '"Akuzatīvs"')
                    line = line.replace('"Dar\uFFFD\uFFFDmā"', '"Darāmā"')
                    line = line.replace('"Darām\uFFFD\uFFFD"', '"Darāmā"')
                    line = line.replace('"Darbības v\uFFFD\uFFFDrds"', '"Darbības vārds"')
                    line = line.replace('"Darb\uFFFD\uFFFDbas vārds"', '"Darbības vārds"')
                    line = line.replace('"Dat\uFFFD\uFFFDvs"', '"Datīvs"')
                    line = line.replace('"Cie\uFFFD\uFFFDamā"', '"Ciešamā"')
                    line = line.replace('"Ciešam\uFFFD\uFFFD"', '"Ciešamā"')
                    line = line.replace('"\uFFFD\uFFFDenitīvs"', '"Ģenitīvs"')
                    line = line.replace('"Ģenit\uFFFD\uFFFDvs"', '"Ģenitīvs"')
                    line = line.replace('"J\uFFFD\uFFFD"', '"Jā"')
                    line = line.replace('"K\uFFFD\uFFFDrta"', '"Kārta"')
                    line = line.replace('"Konjug\uFFFD\uFFFDcija"', '"Konjugācija"')
                    line = line.replace('"Lokat\uFFFD\uFFFDvs"', '"Lokatīvs"')
                    line = line.replace('"Loc\uFFFD\uFFFDjums"', '"Locījums"')
                    line = line.replace('"Nenoteikt\uFFFD\uFFFD"', '"Nenoteiktā"')
                    line = line.replace('"N\uFFFD\uFFFD"', '"Nē"')
                    line = line.replace('"Nominat\uFFFD\uFFFDvs"', '"Nominatīvs"')
                    line = line.replace('"Noteikt\uFFFD\uFFFD"', '"Noteiktā"')
                    line = line.replace('"Noteikt\uFFFD\uFFFDba"', '"Noteiktība"')
                    line = line.replace('"Pag\uFFFD\uFFFDtne"', '"Pagātne"')
                    line = line.replace('"Pak\uFFFD\uFFFDpe"', '"Pakāpe"')
                    line = line.replace('"P\uFFFD\uFFFDrākā"', '"Pārākā"')
                    line = line.replace('"Pār\uFFFD\uFFFDkā"', '"Pārākā"')
                    line = line.replace('"Pārāk\uFFFD\uFFFD"', '"Pārākā"')
                    line = line.replace('"Sievie\uFFFD\uFFFDu"', '"Sieviešu"')
                    line = line.replace('"V\uFFFD\uFFFDrdšķira"', '"Vārdšķira"')
                    line = line.replace('"Vārd\uFFFD\uFFFDķira"', '"Vārdšķira"')
                    line = line.replace('"Vārdš\uFFFD\uFFFDira"', '"Vārdšķira"')
                    line = line.replace('"Visp\uFFFD\uFFFDrākā"', '"Vispārākā"')
                    line = line.replace('"Vispār\uFFFD\uFFFDkā"', '"Vispārākā"')
                    line = line.replace('"Vispārāk\uFFFD\uFFFD"', '"Vispārākā"')
                    line = line.replace('"V\uFFFD\uFFFDriešu"', '"Vīriešu"')
                    line = line.replace('"Vīrie\uFFFD\uFFFDu"', '"Vīriešu"')
                    #line = line.replace('\uFFFD\kajām"', 'ākajām"')
                    if regex.search('\uFFFD', line):
                        regex_res = regex.search('("[^"]+\uFFFD[^"]+")', line)
                        warnings.warn(f"Line with \\uFFFD in value {regex_res.group(1)} skiped!")
                        self.skipped = self.skipped + 1
                        continue
            if not regex.search("^\\s*[\\[\\]]?\\s*$", line):
                try:
                    # json_result = json.loads("{" + line.rstrip(", \n\r") + "}")
                    json_result = json.loads(line)
                except ValueError as e:
                    warnings.warn(f"Following was not parsed into JSON: {line}; {e}")
                    self.bad_lines.append(line)
                    continue
                yield json_result

    def print_bad_line_log(self) -> None:
        if len(self.bad_lines) > 0:
            print(f"\n{len(self.bad_lines)} problem lines encountered.")
            with open("bad_lines.log", 'w', encoding='utf8') as log:
                log.writelines(self.bad_lines)
                max_line_length = len(max(self.bad_lines, key=len))
                min_line_length = len(min(self.bad_lines, key=len))
                log.write(f'\nLongest line: {max_line_length}\n')
                print(f'Longest line: {max_line_length}')
                log.write(f'Shortest line: {min_line_length}\n')
                print(f'Shortest line: {min_line_length}')
                log.close()
        if self.skipped > 0:
            print (f'Skipped {self.skipped} uncorrected lines form processing.')
