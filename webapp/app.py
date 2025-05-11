from flask import Flask, render_template, request
import xml.etree.ElementTree as ET
from pathlib import Path

from .corpus import Corpus, SearchParams


app = Flask(
    __name__, static_url_path="", static_folder="static", template_folder="templates"
)


CORPUS = Corpus(Path.cwd().resolve() / r"data" / r"all_toxic_comments.xml")


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
            "rate": entry.rate,
            "tox_types": entry.tox_types
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

    return render_template("search_results.html", data=xmls)
