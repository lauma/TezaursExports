import regex


def prettify_pronunciation(pronunciation : str) -> str:
    pronunciation = pronunciation.strip()
    pronunciation = regex.sub(',', "\u0327", pronunciation)
    pronunciation = regex.sub('~', "\u0303", pronunciation)
    pronunciation = regex.sub('\\^', "\u0302", pronunciation)
    pronunciation = regex.sub('\\\\', "\u0300", pronunciation)
    pronunciation = regex.sub('/', "\u0301", pronunciation)
    pronunciation = regex.sub('%', "\u02b2", pronunciation)
    pronunciation = regex.sub('n#', "\u014b", pronunciation)
    pronunciation = regex.sub('!', "\u02c8", pronunciation)
    return pronunciation


def prettify_text_with_pronunciation(text : str) -> str:
    return regex.sub(r"\[[^\[\]]+]", lambda x: prettify_pronunciation(x.group(0)), text)
