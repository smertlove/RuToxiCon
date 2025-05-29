import xml.etree.ElementTree as ET

import razdel
import pymorphy3 as pm
from functools import lru_cache
from string import punctuation
from collections import Counter
from uuid import uuid4
from functools import reduce


def get_all_text(et: ET):
    text = et.text or ""
    for child in et:
        text += get_all_text(child)
        text += (child.tail or "")
    return text


class Lemmatizer:

    morph = pm.MorphAnalyzer()

    @classmethod
    @lru_cache(123456789)
    def lemmatize(cls, word:str) -> str:
        return cls.morph.parse(word)[0].normal_form


def get_all_lemmas(sent: str, punc=set(punctuation)) -> list[str]:
    tokens = [tok.text for tok in razdel.tokenize(sent)]
    return [Lemmatizer.lemmatize(tok) for tok in tokens if tok not in punc]


class CorpusEntry:

    def __init__(self, et: ET):

        self.uuid = uuid4()
        self.xml = et

        self.tokens = Counter(
            get_all_lemmas(
                get_all_text(self.xml).strip()
            )
        )

        lex_tokens = [c.text.lower() for c in self.xml.findall(".//lex")]
        lex_lemmas = [Lemmatizer.lemmatize(c) for c in lex_tokens]

        self.lex_tokens = Counter(lex_tokens)
        self.lex_lemmas = Counter(lex_lemmas)

        self.rate = min(
            sum(
                [
                    int(c.attrib["rate"])
                    for c
                    in self.xml.findall(".//tox")
                ]
            ),
            10
        )

        self.responses = [c.attrib["response"].replace(" ", "").lower() for c in self.xml.findall(".//tox")]
        self.tox_types = [c.attrib["type"].replace(" ", "").lower() for c in self.xml.findall(".//tox")]
        self.phrase_types = [c.attrib["type"].replace(" ", "").lower() for c in self.xml.findall(".//phrase")]

    def __hash__(self):
        return hash(self.uuid)
    
    def __repr__(self):
        return (
            self.__class__.__name__ + ":\n"
            + ET.tostring(self.xml, encoding="utf8").decode("utf-8") + "\n"
            + str(self.tokens) + "\n"
            + str(self.lex_tokens) + "\n"
            + str(self.lex_lemmas) + "\n"
            + "rate=" + str(self.rate) + "\n"
            + str(self.responses) + "\n"
            + str(self.tox_types) + "\n"
            + str(self.phrase_types)
        )


class SearchParams:

    def __init__(
        self,
        query="",
        rate_start=0,
        rate_end=10,
        responses=[],
        tox_types=[],
        phrase_types = []
    ):
        self.query = query
        self.rate_start = rate_start
        self.rate_end = rate_end
        self.responses = responses
        self.tox_types = tox_types
        self.phrase_types = phrase_types

    def __repr__(self):
        return f"{self.__class__.__name__}({self.query}, {self.rate_start}-{self.rate_end}, {self.responses}, {self.tox_types}, {self.phrase_types})"


class Corpus:

    def __init__(self, path: str):

        self.entries: dict[int, CorpusEntry] = dict()
        self.lemma_index       = dict()
        self.rate_index        = dict()
        self.response_index    = dict()
        self.tox_type_index    = dict()
        self.phrase_type_index = dict()

        with open(path, "r", encoding="utf-8") as file:
            xml_data = file.read()

        data = ET.fromstring(xml_data)

        for text in data:
            self.append(text)

        self.build_index()

    def __getitem__(self, i):
        return self.entries[i]

    def __len__(self):
        return len(self.entries)

    def append(self, et):
        self.entries[len(self)] = CorpusEntry(et)

    def __repr__(self):
        return f"{self.__class__.__name__}({len(self)} entries)"

    def build_index(self):

        for i, entry in self.entries.items():

            for token in entry.tokens:
                self.lemma_index[token] = self.lemma_index.get(token, set()) | {i}

            self.rate_index[entry.rate] = self.rate_index.get(entry.rate, set()) | {i}

            for response in entry.responses:
                self.response_index[response] = self.response_index.get(response, set()) | {i}
                if ":" in response:
                    response = response.split(":", maxsplit=1)[0]
                    self.response_index[response] = self.response_index.get(response, set()) | {i}

            for tox_type in entry.tox_types:
                self.tox_type_index[tox_type] = self.tox_type_index.get(tox_type, set()) | {i}
                if ":" in tox_type:
                    tox_type = tox_type.split(":", maxsplit=1)[0]
                    self.tox_type_index[tox_type] = self.tox_type_index.get(tox_type, set()) | {i}

            for phrase_type in entry.phrase_types:
                self.phrase_type_index[phrase_type] = self.phrase_type_index.get(phrase_type, set()) | {i}

    def search(self, params:SearchParams) -> list[int]:

        # Множество записей с подходящими леммами
        sets = [
            self.lemma_index.get(token, set())
            for token
            in get_all_lemmas(params.query)
        ]

        # Множество записей с подходящими rate
        sets.append(
            reduce(
                lambda s1, s2: s1 | s2,
                [
                    self.rate_index.get(id_, set())
                    for id_
                    in range(params.rate_start, params.rate_end + 1)
                ]
            )
        )

        # Множество записей с подходящими responses
        if params.responses:
            sets.append(
                reduce(
                    lambda s1, s2: s1 | s2,
                    [
                        self.response_index.get(response, set())
                        for response
                        in params.responses
                    ]
                )
            )

        # Множество записей с подходящими tox_types
        if params.tox_types:
            sets.append(
                reduce(
                    lambda s1, s2: s1 | s2,
                    [
                        self.tox_type_index.get(tox_type, set())
                        for tox_type
                        in params.tox_types
                    ]
                )
            )

        # Множество записей с подходящими phrase_types
        if params.phrase_types:
            sets.append(
                reduce(
                    lambda s1, s2: s1 | s2,
                    [
                        self.phrase_type_index.get(phrase_type, set())
                        for phrase_type
                        in params.phrase_types
                    ]
                )
            )

        return reduce(lambda s1, s2: s1 & s2, sets)
