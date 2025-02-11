import re
from pathlib import Path

import bs4
import six.moves.urllib.request

from ..base_parser import BaseDocumentationParser
from ..parser_registry import ParserRegistry


__all__ = ['KlipperGcodeDocumentationParser']


@ParserRegistry.register_parser
class KlipperGcodeDocumentationParser(BaseDocumentationParser):
    """Klipper documentation parser"""

    ID = "klipper"
    SOURCE = "Klipper"
    URL = "https://www.klipper3d.org/G-Codes.html"
    SOURCE_URL = URL
    re_reprap = re.compile(r"^([GM]\d+)(?:\s(.*))?$")
    re_klipper = re.compile(r"^([A-Z][A-Z_]+)(?:\s(.*))?$")

    def load_and_parse_all_codes(self, directory):
        with self.latest_documentation_directory(directory) as directory:
            document = bs4.BeautifulSoup(
                Path(directory).joinpath("g-codes.html").read_text('utf8'),
                "html.parser")
        return self.get_all_codes(document)

    def populate_temporary_directory(self, directory):
        html_filename = str(Path(directory).joinpath("g-codes.html"))
        six.moves.urllib.request.urlretrieve(self.SOURCE_URL, html_filename)

    def get_all_codes(self, document):
        """Get all the GCodes from the document"""
        code_fragments_list_items_and_siblings = (
            (code.text.replace('\n', ' '), code.find_parent('li'),
             code.next_siblings)
            for code in document.select('li code:nth-of-type(1)')
        )

        return dict(filter(None, map(
            self.parse_code, code_fragments_list_items_and_siblings)))

    def parse_code(self, code_fragments_list_items_and_siblings):
        """Parse a GCode section"""
        code_fragment, list_item, siblings = \
            code_fragments_list_items_and_siblings
        if self.re_reprap.match(code_fragment):
            return self.parse_reprap_code(code_fragment, list_item)
        elif self.re_klipper.match(code_fragment):
            return self.parse_klipper_code(code_fragment, list_item, siblings)
        else:
            return None

    def parse_reprap_code(self, code_fragment, list_item):
        """Parse RepRap formatted code"""
        code, parameters_text = self.re_reprap.match(code_fragment).groups()
        previous_text = " ".join(
            sibling
            for sibling in list_item.previous_siblings
            if isinstance(sibling, str)
        ).strip().strip(":")
        return (code, [{
            "title": previous_text,
            "brief": "",
            "codes": [code],
            "related": [],
            "parameters": self.parse_reprap_parameters(parameters_text),
            "source": self.SOURCE,
            "url": f"{self.URL}#{self.find_previous_id(list_item)}",
        }])

    def parse_reprap_parameters(self, parameters_text):
        """Parse RepRap formatted parameters"""
        if not parameters_text:
            return []
        parameter_texts = map(str.strip, parameters_text.split(" "))
        return list(filter(None, map(
            self.parse_reprap_parameter, parameter_texts)))

    def parse_reprap_parameter(self, parameter_text):
        """Parse a RepRap formatted parameter"""
        if not parameter_text:
            return None
        optional = (
            parameter_text.startswith('[')
            or parameter_text.endswith(']')
        )
        parameter_text = parameter_text.replace('[', '').replace(']', '')
        if parameter_text.startswith('<'):
            parameter_text = parameter_text.replace('<', '').replace('>', '')
            tag = parameter_text
            label = f"<{parameter_text}>"
        elif '<' in parameter_text:
            tag = parameter_text[:parameter_text.index('<')]
            parameter_text = parameter_text.replace('<', '').replace('>', '')
            label = f"{tag}<{parameter_text}>"
        else:
            tag = parameter_text
            label = parameter_text
        if optional:
            label = f"[{label}]"
        return {
            "tag": tag,
            "optional": optional,
            "description": "",
            "values": [],
            "label": label,
        }

    def find_previous_id(self, element):
        """Get the first ID from a previous sibling"""
        id_element = next((
            id_element
            for id_element in filter(None, (
                sibling
                for parent in reversed(element.find_parents())
                for sibling in parent.find_previous_siblings(None, {'id': True})
            ))
            if id_element.name != "input"
        ), None)
        if not id_element:
            return ''

        return id_element.attrs['id']

    def parse_klipper_code(self, code_fragment, list_item, siblings):
        """Parse a Klipper GCode"""
        code, parameters_text = self.re_klipper.match(code_fragment).groups()
        next_text = next(filter(None, siblings), "")\
            .replace('\n', '').strip().strip(':').strip()
        return (code, [{
            "title": next_text.split('.')[0],
            "brief": next_text,
            "codes": [code],
            "related": [],
            "parameters": self.parse_klipper_parameters(parameters_text),
            "source": self.SOURCE,
            "url": f"{self.URL}#{self.find_previous_id(list_item)}",
        }])

    def parse_klipper_parameters(self, parameters_text):
        """Parse Klipper parameters"""
        if not parameters_text:
            return []
        parameter_texts = map(str.strip, parameters_text.split(" "))
        return list(filter(None, map(
            self.parse_klipper_parameter, parameter_texts)))

    def parse_klipper_parameter(self, parameter_text):
        """Parse a Klipper parameter"""
        if not parameter_text:
            return None
        optional = (
            parameter_text.startswith('[')
            or parameter_text.endswith(']')
        )
        parameter_text = parameter_text.replace('[', '').replace(']', '')
        label = parameter_text
        if parameter_text.startswith('<'):
            parameter_text = parameter_text.replace('<', '').replace('>', '')
            tag = parameter_text
        elif '<' in parameter_text:
            tag = parameter_text[:parameter_text.index('<')].replace('=', '')
        else:
            tag = parameter_text.replace('=', '')
        return {
            "tag": tag,
            "optional": optional,
            "description": "",
            "values": [],
            "label": label,
        }
