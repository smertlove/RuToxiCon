from flask import Flask, render_template, request, abort
import xml.etree.ElementTree as ET
from pathlib import Path

import re

from .corpus import Corpus, SearchParams, get_all_text


app = Flask(
    __name__, static_url_path="", static_folder="static", template_folder="templates"
)


CORPUS = Corpus(
    Path.cwd().resolve() / r"data" / r"all_toxic_comments.xml",
    # "lemmatizer"
    "stemmer"
    # None
)


PHRASE_TYPES = sorted(CORPUS.phrase_type_index.keys())
TOX_TYPES = sorted(CORPUS.tox_type_index.keys())
RESPONSES = sorted(CORPUS.response_index.keys())


@app.route("/")
def warning():
    return render_template("warning.html")


@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/search_plus")
def search_plus():
    return render_template(
        "search_plus.html",
        phrase_types=PHRASE_TYPES,
        tox_types=TOX_TYPES,
        responses=RESPONSES,
    )


@app.route("/search_results")
def search_results():
    search_term = request.args.get("search_term", "")

    search_regex = request.args.get("search_regex", "").strip()

    rating_from = request.args.get("rating_from", 0, type=int)
    rating_to = request.args.get("rating_to", 10, type=int)
    if rating_from > rating_to:
        rating_from, rating_to = rating_to, rating_from

    tox_types = request.args.getlist("tox_types")
    phrase_types = request.args.getlist("phrase_types")
    responses = request.args.getlist("responses")

    xmls = [
        {
            "xml": ET.tostring(
                (entry := CORPUS[i]).xml,
                encoding="unicode"
            ).strip(),
            "text": get_all_text(entry.xml),
            "rate": entry.rate,
            "tox_types": ", ".join(entry.tox_types),
            "phrase_types": ", ".join(entry.phrase_types),
            "responses": ", ".join(entry.responses),
            "regex_match": None,
            "entry": entry
        }
        for i
        in CORPUS.search(
            SearchParams(
                query=search_term,
                rate_start=rating_from,
                rate_end=rating_to,
                responses=responses,
                tox_types=tox_types,
                phrase_types=phrase_types
            )
        )
    ]

    if search_regex:
        try:
            regex = re.compile(search_regex)
            new_xmls = []
            for entry in xmls:
                m = regex.search(entry["text"])
                if m:
                    entry["regex_match"] = '"' + m.group() + '"'
                    new_xmls.append(entry)

            xmls = new_xmls

        except re.error:
            abort(422, description=f"Invalid regex pattern {search_regex}")

    xmls.sort(key=lambda elem: elem["rate"])

    lex_counts = [sum(entry["entry"].lex_lemmas.values()) for entry in xmls]
    token_counts = [sum(entry["entry"].tokens.values()) for entry in xmls]
    rates = [entry["entry"].rate for entry in xmls]

    stats = {
        "tokens_tot": sum(token_counts),
        "tokens_min": min(token_counts),
        "tokens_max": max(token_counts),
        "tokens_avg": sum(token_counts) / len(token_counts),
        "lex_tot": sum(lex_counts),
        "lex_min": min(lex_counts),
        "lex_max": max(lex_counts),
        "lex_avg": sum(lex_counts) / len(lex_counts),
        "rate_tot": sum(rates),
        "rate_min": min(rates),
        "rate_max": max(rates),
        "rate_avg": sum(rates) / len(rates),
    }

    return render_template("search_results.html", data=xmls, stats=stats)
