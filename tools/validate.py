from argparse import ArgumentParser
from pathlib import Path

import xml.etree.ElementTree as ET

import re


DEFAULT      = "\033[0m"
BOLD_RED     = "\033[1;31m"
ITALIC_GREEN = "\033[3;32m"


class XmlValidator:

    parse_error_ptrn = re.compile(
        r".*line (\d+), column (\d+).*"
    )

    span = 20

    @classmethod
    def validate(cls, xml_string):

        if not cls.validate_standard(xml_string):
            return False

        if not cls.validate_markup(xml_string):
            return False

        return True

    @classmethod
    def validate_standard(cls, xml_string):
        print("Checking xml syntax: ", end="")

        try:
            ET.fromstring(xml_string)

        except ET.ParseError as e:
            print(BOLD_RED + "ERR" + DEFAULT)
            print(f"XML Validation Error: {e}")

            matchobj = cls.parse_error_ptrn.match(str(e))
            if matchobj:
                row, col = map(int, matchobj.groups())

                line = xml_string.split("\n")[row-1]

                start = max(0, col-cls.span)
                end = min(len(line), col+cls.span)

                print(line[start:end])
                print(BOLD_RED + "-"*(col-start) + "^" + DEFAULT)

            return False

        else:
            print(ITALIC_GREEN + "OK!" + DEFAULT)
            return True

    @classmethod
    def validate_markup(cls, xml_string):
        print("Checking markup: ", end="")

        try:
            tree = ET.fromstring(xml_string)

            for tox_element in tree.findall(".//tox"):

                tox_string = ET.tostring(tox_element, encoding='unicode', method='xml')

                for attr in ["rate", "type", "response"]:
                    if attr not in tox_element.attrib:
                        print(BOLD_RED + "ERR" + DEFAULT)
                        print(f"Error: {tox_string} tag is missing '{attr}' attribute.")
                        return False

                rate_value = tox_element.attrib["rate"]
                try:
                    rate_int = int(rate_value)
                    if not 1 <= rate_int <= 10:
                        print(BOLD_RED + "ERR" + DEFAULT)
                        print(f"Error: {tox_string} 'rate' attribute value '{rate_value}' is not an integer between 1 and 10.")
                        return False
                except ValueError:
                    print(BOLD_RED + "ERR" + DEFAULT)
                    print(f"Error: {tox_string} 'rate' attribute value '{rate_value}' is not an integer.")
                    return False

                type_value = tox_element.attrib["type"]
                if type_value not in {
                    "threat",
                    "general_insult",
                    "harassment",
                    "profanity",
                    "hate_speech",
                    "hate_speech: lgbtq*",
                    "hate_speech: gender",
                    "hate_speech: race",
                    "hate_speech: religion",
                    "hate_speech: nationality",
                    }:
                    print(f"Error: {tox_string} 'type' attribute value '{type_value}' is invalid.")
                    return False

                response_value = tox_element.attrib["response"]
                if response_value not in {
                    "person",
                    "author",
                    "post: animate",
                    "post: inanimate"
                    }:
                    print(f"Error: {tox_string} 'response' attribute value '{response_value}' is invalid.")
                    return False

            for phrase_element in tree.findall(".//phrase"):
                phrase_string = ET.tostring(phrase_element, encoding='unicode', method='xml')

                if "type" not in tox_element.attrib:
                    print(BOLD_RED + "ERR" + DEFAULT)
                    print(f"Error: {phrase_string} tag is missing 'type' attribute.")
                    return False
                
                type_value = phrase_element.attrib["type"]
                if type_value not in {
                    "direct", "indirect"
                }:
                    print(f"Error: {phrase_string} 'type' attribute value '{type_value}' is invalid.")

        except ET.ParseError as e:
            print(BOLD_RED + "ERR" + DEFAULT)
            print(f"XML Validation Error during markup check: {e}")
            return False
        else:
            print(ITALIC_GREEN + "OK!" + DEFAULT)
            return True


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--path", "-p", help="Path to toxic file.")

    args = parser.parse_args()
    path = Path(args.path)

    if not path.exists():
        print(f"No such file or directory: '{str(path)}'")

    else:
        with open(path, "r", encoding="utf-8") as file:
            xml_data = file.read()

        if XmlValidator.validate(xml_data):
            print(ITALIC_GREEN + "XML is valid." + DEFAULT)
        else:
            print(BOLD_RED + "XML is invalid!" + DEFAULT)
