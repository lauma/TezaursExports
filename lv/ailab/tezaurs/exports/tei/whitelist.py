from typing import Any

import regex


class EntryDesc:
    def __init__(self, entry_name, homonym = 0):
        self.entry_name : str = entry_name
        self.homonym : int = homonym

    def __eq__(self, other : Any) -> bool:
        if self is other:
            return True
        if other is None:
            return False
        return isinstance(other, EntryDesc) and self.entry_name == other.entry_name and self.homonym == other.homonym

    def __ne__(self, other : Any) -> bool:
        return not self == other


class EntryWhitelist:

    def __init__(self):
        self.entries = []

    def load(self, file_name : str) :
        with open(file_name, 'r', encoding='utf8') as f:
            for line in f:
                line = line.strip()
                parts = regex.split('\\s*\t\\s*', line)
                if len(parts) == 2:
                    self.entries.append(EntryDesc(parts[0], int(parts[1])))
                elif len(parts) == 1 and parts[0]:
                    self.entries.append(EntryDesc(parts[0]))
                elif len(parts) > 0:
                    print(f'Weird line in entry list: "{line}"!')

    def check(self, entry_name : str, homonym : int) -> bool:
        return EntryDesc(entry_name, homonym) in self.entries
