import regex

superscript : dict[str, str] = {
    '1': "\u00B9",
    '2': "\u00B2",
    '3': "\u00B3",
    '0': "\u2070",
    '4': "\u2074",
    '5': "\u2075",
    '6': "\u2076",
    '7': "\u2077",
    '8': "\u2078",
    '9': "\u2079",
    '+': "\u207A",
    '-': "\u207B",
    '\u2013': "\u207B",
    '=': "\u207C",
    '(': "\u207D",
    ')': "\u207E",
    'i': "\u2071",
    'k': "\u1D4F",
    'n': "\u207F",
    'x': "\u20E3",
    'g': "\u1D4D",
}
subscript : dict[str, str] = {
    '0': "\u2080",
    '1': "\u2081",
    '2': "\u2082",
    '3': "\u2083",
    '4': "\u2084",
    '5': "\u2085",
    '6': "\u2086",
    '7': "\u2087",
    '8': "\u2088",
    '9': "\u2089",
    '+': "\u208A",
    '-': "\u208B",
    "\u2013": "\u208B",
    '=': "\u208C",
    '(': "\u208D",
    ')': "\u208E",
    'a': "\u2090",
    'e': "\u2091",
    'o': "\u2092",
    'x': "\u2093",
    'h': "\u2095",
    'k': "\u2096",
    'l': "\u2097",
    'm': "\u2098",
    'n': "\u2099",
    'p': "\u209A",
    's': "\u209B",
    't': "\u209C",

    'i': "\u1D62",
    'r': "\u1D63",
    'j': "\u2C7C",
    "\u03B3": "\u1D67", # gamma
}


def _convert_to_sup(text : str, debug_text : str) -> str:
    result = regex.sub(r'^[o0O]^(\s?[CF])', "\u00B0\\1", text) #grādu normalizācija
    warns = regex.findall('[^' + regex.escape(''.join(superscript.keys())) + ']', result)
    if warns:
        print(', '.join(warns) + " was not transformed to superscript in string \"" + result
              + "\" for full text \"" + debug_text + "\"!")
    result = result.translate(str.maketrans(superscript))
    return result


def _convert_to_sub(text : str, debug_text : str) -> str:
    warns = regex.findall('[^' + regex.escape(''.join(subscript.keys())) + ']', text)
    if warns:
        print(', '.join(warns) + " was not transformed to subscript in string \"" + text
              + "\" for full text \"" + debug_text + "\"!")
    result = text.translate(str.maketrans(subscript))
    return result


def normalize_scripts(gloss : str) -> str:
    result = gloss
    result = regex.sub(r'(?<!\\)\^([^ ]*?[^ \\])\^', lambda x: _convert_to_sup(x.group(1), gloss), result)
    result = regex.sub(r'(?<!\\)~([^ ]*?[^ \\])~', lambda x: _convert_to_sub(x.group(1), gloss), result)
    return result


def full_cleanup(gloss : str) -> str:
    result = gloss
    result = _remove_anchor_links(result)
    result = normalize_scripts(result)
    result = mandatory_normalization(result)
    result = _remove_emphasis(result)
    result = _unescape_tez_md(result)
    return result


def _remove_anchor_links(gloss : str) -> str:
    result = regex.sub(r'\[((?:\p{L}\p{M}*)+)\]\{[sen]:\d+\}', r'\1', gloss)
    return result


def _remove_emphasis(gloss : str) -> str:
    result = gloss
    result = regex.sub('</?(em|i|small|b) ?/?>', '', result)
    result = regex.sub(r'(?<!\\)_+([^_]*[^_\\])_+', r'\1', result)
    return result


def mandatory_normalization(gloss : str) -> str:
    result = gloss
    result = _symbol_normalization(result)
    result = _normalize_spacing(result)
    return result


def _symbol_normalization(gloss : str) -> str:
    result = gloss
    result = regex.sub('-->', '→', result)
    #result = regex.sub('->', '→', result)
    result = regex.sub('--', '–', result)
    result = regex.sub('---', '—', result)
    result = regex.sub('\\.\\.\\.', '…', result)
    result = regex.sub('\\.\\.', '‥', result)

    return result


def _normalize_spacing(gloss : str) -> str:
    result = gloss
    result = regex.sub('\\n', ' ', result)
    result = regex.sub('  +', ' ', result)
    return result


def _unescape_tez_md(gloss : str) -> str:
    result = gloss
    result = regex.sub(r'\\_', '_', result)
    result = regex.sub(r'\\\^', '^', result)
    result = regex.sub(r'\\~', '~', result)
    return result

