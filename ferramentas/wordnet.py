"""Capa «wordnet»: sentidos de cada lema galego segundo Galnet (Open Multilingual Wordnet).

    python3 ferramentas/wordnet.py   ->  datos/capas/wordnet.jsonl

Galnet non trae definicións en galego e o WordNet de Princeton dáas en inglés.
Neste repositorio non se gardan definicións en inglés: cada sentido leva a
definición do WordNet traducida ao galego (datos/traducions/definicions-wordnet.tsv,
identificador do sentido -> definición), os sinónimos galegos do mesmo sentido
e os equivalentes en castelán, portugués e inglés. É semántica aberta
(CC BY 3.0). A táboa cobre os 19 311 sentidos (synsets) de Galnet; se unha versión
nova trae algún máis, queda sen definición ata que se traduza.

Formato:
    {"lema": "casa", "categoria": "substantivo", "capa": "wordnet",
     "sentidos": [{"ili": "i...", "definicion": "...", "sinonimos": [...],
                   "es": [...], "pt": [...], "en": [...]}], "fontes": [...]}
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importar as I  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
OMW = RAIZ / "fontes" / "cache" / "omw"
SAIDA = RAIZ / "datos" / "capas" / "wordnet.jsonl"
TRADUCIONS = RAIZ / "datos" / "traducions" / "definicions-wordnet.tsv"

CATEGORIAS = {"n": "substantivo", "v": "verbo", "a": "adxectivo", "s": "adxectivo", "r": "adverbio"}


def ler_lexicon(ruta: Path):
    """(ili -> [lemas]) e (ili -> definición) dun ficheiro LMF do OMW."""
    lemas: dict[str, list[str]] = defaultdict(list)
    definicions: dict[str, str] = {}
    pos_por_ili: dict[str, str] = {}
    entradas: dict[str, tuple[str, str]] = {}   # id de LexicalEntry -> (lema, pos)
    sentidos: dict[str, list[str]] = defaultdict(list)   # synset id -> [lemas]
    for _, el in ET.iterparse(ruta, events=("end",)):
        tag = el.tag.split("}")[-1]
        if tag == "LexicalEntry":
            lema = el.find("Lemma")
            forma = lema.get("writtenForm")
            pos = lema.get("partOfSpeech")
            for sense in el.findall("Sense"):
                sentidos[sense.get("synset")].append(forma)
            entradas[el.get("id")] = (forma, pos)
            el.clear()
        elif tag == "Synset":
            ili = el.get("ili")
            if ili and ili != "in":
                pos_por_ili[ili] = el.get("partOfSpeech")
                for forma in sentidos.get(el.get("id"), []):
                    if forma not in lemas[ili]:
                        lemas[ili].append(forma)
                d = el.find("Definition")
                if d is not None and d.text:
                    definicions[ili] = d.text.strip()
            el.clear()
    return lemas, definicions, pos_por_ili


def ler_traducions(ruta: Path = TRADUCIONS) -> dict[str, str]:
    """ili -> definición do WordNet en galego."""
    traducions = {}
    if ruta.exists():
        with ruta.open(encoding="utf-8") as fh:
            for liña in fh:
                campos = liña.rstrip("\n").split("\t")
                if len(campos) == 2 and not liña.startswith("#"):
                    traducions[campos[0]] = campos[1]
    return traducions


def main() -> None:
    gl, _, pos_gl = ler_lexicon(OMW / "omw-gl" / "omw-gl.xml")
    en, _, _ = ler_lexicon(OMW / "omw-en" / "omw-en.xml")
    definicions = ler_traducions()
    es, _, _ = ler_lexicon(OMW / "omw-es" / "omw-es.xml")
    pt, _, _ = ler_lexicon(OMW / "omw-pt" / "omw-pt.xml")

    por_lema: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for ili, formas in gl.items():
        categoria = CATEGORIAS.get(pos_gl.get(ili, ""), "")
        sentido_base = {"ili": ili}
        if definicions.get(ili):
            sentido_base["definicion"] = definicions[ili]
        for lingua, dic in (("es", es), ("pt", pt), ("en", en)):
            if dic.get(ili):
                sentido_base[lingua] = dic[ili]
        for forma in formas:
            sentido = dict(sentido_base)
            sinonimos = [f for f in formas if f != forma]
            if sinonimos:
                sentido["sinonimos"] = sinonimos
            por_lema[(forma, categoria)].append(sentido)

    n = 0
    with SAIDA.open("w", encoding="utf-8") as fh:
        for (lema, categoria) in sorted(por_lema, key=lambda k: (I.clave_orde(k[0]), k[1])):
            r = {"lema": lema, "categoria": categoria, "capa": "wordnet", "sentidos": por_lema[(lema, categoria)],
                 "fontes": ["galnet", "omw-en", "omw-es", "omw-pt"]}
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    print(f"datos/capas/wordnet.jsonl: {n} lemas, {sum(len(v) for v in por_lema.values())} sentidos")


if __name__ == "__main__":
    main()
