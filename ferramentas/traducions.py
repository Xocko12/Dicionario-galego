"""Capa «traducions»: equivalentes en castelán, portugués e inglés (Apertium, GPL).

    python3 ferramentas/traducions.py   ->  datos/capas/traducions.jsonl

Le os dicionarios bilingües de Apertium (es-gl, spa-glg, pt-gl, en-gl); neles o
galego é o lado dereito (<r>). Tómanse os pares nas dúas direccións: para un
dicionario, «silla → cadeira» (só es→gl en Apertium) tamén di que «cadeira»
se traduce por «silla».

Formato:
    {"lema": "cadeira", "categoria": "substantivo", "capa": "traducions",
     "es": ["silla"], "pt": ["cadeira"], "en": ["chair"], "fontes": ["apertium-es-gl", ...]}
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importar as I  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "fontes" / "cache" / "apertium"
SAIDA = RAIZ / "datos" / "capas" / "traducions.jsonl"

DICIONARIOS = [("es", "es-gl.dix"), ("es", "spa-glg.dix"), ("pt", "pt-gl.dix"), ("en", "en-gl.dix")]
CATEGORIAS = {"n": "substantivo", "adj": "adxectivo", "vblex": "verbo", "vbser": "verbo", "vbhaver": "verbo",
              "vbmod": "verbo", "adv": "adverbio", "pr": "preposición", "cnjcoo": "conxunción",
              "cnjsub": "conxunción", "cnjadv": "conxunción", "ij": "interxección", "num": "numeral",
              "prn": "pronome", "det": "determinante", "preadv": "adverbio", "predet": "determinante"}
OMITIR = {"np", "ant", "top", "cog", "al", "org"}   # nomes propios


def texto_e_categoria(el) -> tuple[str, str | None]:
    """Texto dun <l> ou <r> (con <b/> como espazo, sen <g>) e a primeira etiqueta <s>."""
    partes = []
    etiquetas = []

    def percorrer(nodo, dentro=False):
        if nodo.text and not dentro:
            partes.append(nodo.text)
        for fillo in nodo:
            tag = fillo.tag
            if tag == "b":
                partes.append(" ")
            elif tag == "s":
                etiquetas.append(fillo.get("n"))
            elif tag == "g":
                percorrer(fillo)
            if fillo.tail:
                partes.append(fillo.tail)

    percorrer(el)
    texto = re.sub(r"\s+", " ", "".join(partes)).strip()
    return texto, etiquetas[0] if etiquetas else None


def ler_dix(ruta: Path):
    """[(galego, categoría, outra lingua)] das entradas válidas gl -> outra."""
    saida = []
    for _, e in ET.iterparse(ruta, events=("end",)):
        if e.tag != "e":
            continue
        p = e.find("p")
        if p is None:
            e.clear()
            continue
        l, r = p.find("l"), p.find("r")
        if l is None or r is None:
            e.clear()
            continue
        outro, _ = texto_e_categoria(l)
        galego, etiqueta = texto_e_categoria(r)
        if galego and outro and etiqueta not in OMITIR and galego[0].islower():
            saida.append((galego, CATEGORIAS.get(etiqueta, etiqueta or ""), outro))
        e.clear()
    return saida


def main() -> None:
    rexistros: dict[tuple[str, str], dict] = {}
    for lingua, nome in DICIONARIOS:
        ruta = CACHE / nome
        if not ruta.exists():
            continue
        fonte = "apertium-" + nome[:-4]
        for galego, categoria, outro in ler_dix(ruta):
            r = rexistros.setdefault((galego, categoria), {"lema": galego, "categoria": categoria,
                                                            "capa": "traducions", "fontes": []})
            lista = r.setdefault(lingua, [])
            if outro not in lista:
                lista.append(outro)
            if fonte not in r["fontes"]:
                r["fontes"].append(fonte)
    n = 0
    with SAIDA.open("w", encoding="utf-8") as fh:
        for clave in sorted(rexistros, key=lambda k: (I.clave_orde(k[0]), k[1])):
            r = rexistros[clave]
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    linguas = {l: sum(1 for r in rexistros.values() if r.get(l)) for l in ("es", "pt", "en")}
    print(f"datos/capas/traducions.jsonl: {n} lemas; con castelán {linguas['es']}, portugués {linguas['pt']}, inglés {linguas['en']}")


if __name__ == "__main__":
    main()
