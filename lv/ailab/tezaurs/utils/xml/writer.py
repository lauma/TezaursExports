from io import TextIOWrapper
from typing import Optional
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl


class XMLWriter:

    DEFAULT_INDENT_CHARS : str = "  "
    DEFAULT_NEWLINE_CHARS : str = "\n"

    def __init__(self, file : TextIOWrapper, indent_chars : str = DEFAULT_INDENT_CHARS,
                 newline_chars : str = DEFAULT_NEWLINE_CHARS):
        self.indent_chars : str = indent_chars
        self.newline_chars : str = newline_chars
        self.file = file
        self.gen : XMLGenerator = XMLGenerator(file, 'UTF-8', True)
        self.xml_depth : int = 0


    def start_node_simple(self, name : str, attrs : dict[str, str]) -> None:
        self.gen.startElement(name, AttributesImpl(attrs))


    def end_node_simple(self, name : str) -> None:
        self.gen.endElement(name)


    def start_node_with_ws(self, name : str, attrs : dict[str, str]) -> None:
        self.gen.ignorableWhitespace(self.indent_chars * self.xml_depth)
        self.gen.startElement(name, AttributesImpl(attrs))
        self.gen.ignorableWhitespace(self.newline_chars)
        self.xml_depth = self.xml_depth + 1


    def end_node_with_ws(self, name : str) -> None:
        self.xml_depth = self.xml_depth - 1
        self.gen.ignorableWhitespace(self.indent_chars * self.xml_depth)
        self.gen.endElement(name)
        self.gen.ignorableWhitespace(self.newline_chars)


    def do_simple_leaf_node(self, name : str, attrs : dict[str, str], content : Optional[str] = None) -> None:
        self.gen.ignorableWhitespace(self.indent_chars * self.xml_depth)
        self.gen.startElement(name, AttributesImpl(attrs))
        if content:
            self.gen.characters(content)
        self.gen.endElement(name)
        self.gen.ignorableWhitespace(self.newline_chars)


    def start_document(self, doctype : Optional[str] = None) -> None:
        self.gen.startDocument()
        if doctype:
            self.file.write(doctype)
            self.file.write(self.newline_chars)


    def end_document(self) -> None:
        self.gen.endDocument()
