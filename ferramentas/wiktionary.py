"""Definicións abertas desde o Wiktionary (CC BY-SA), para executar nunha
máquina con acceso a wikimedia.org (desde o contorno onde se construíu este
proxecto non se pode).

Dúas fontes, dúas capas:

  1. Galipedia... non: o **Wiktionary galego** (gl.wiktionary.org): definicións
     EN GALEGO. Lese do volcado XML:
         https://dumps.wikimedia.org/glwiktionary/latest/glwiktionary-latest-pages-articles.xml.bz2
     -> datos/capas/definicions-gl.jsonl

  2. O **Wiktionary inglés**, entradas galegas, xa procesadas por wiktextract
     (kaikki.org), con definicións en inglés e moitas máis entradas:
         https://kaikki.org/dictionary/Galician/kaikki.org-dictionary-Galician.jsonl
     -> datos/capas/definicions-en.jsonl

Uso:
    python3 ferramentas/wiktionary.py --descargar          # baixa os dous ficheiros a fontes/cache/wiktionary/
    python3 ferramentas/wiktionary.py                      # procesa o que haxa en fontes/cache/wiktionary/
    python3 ferramentas/wiktionary.py --gl ficheiro.xml.bz2 --en ficheiro.jsonl

Formato de saída (as dúas capas):
    {"lema": "casa", "categoria": "substantivo", "capa": "definicions-gl",
     "acepcions": [{"definicion": "...", "exemplos": [...]}], "fontes": ["wiktionary-gl"],
     "licenza": "CC-BY-SA-4.0", "url": "https://gl.wiktionary.org/wiki/casa"}

O analizador do Wiktionary galego é conservador: colle as liñas de definición
(«# …») das seccións galegas e limpa as ligazóns e os modelos máis comúns; o
que non recoñece queda fóra, nunca se inventa. Revisa unha mostra ao primeiro
uso e adapta `LIMPAR` se fai falta.
"""

from __future__ import annotations

import bz2
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "fontes" / "cache" / "wiktionary"
SAIDA = RAIZ / "datos" / "capas"

URL_GL = "https://dumps.wikimedia.org/glwiktionary/latest/glwiktionary-latest-pages-articles.xml.bz2"
URL_EN = "https://kaikki.org/dictionary/Galician/kaikki.org-dictionary-Galician.jsonl"

# Cabeceiras de sección do Wiktionary galego -> categoría
CATEGORIAS_GL = {
    "substantivo": "substantivo", "nome": "substantivo", "adxectivo": "adxectivo", "verbo": "verbo",
    "adverbio": "adverbio", "pronome": "pronome", "preposición": "preposición", "conxunción": "conxunción",
    "interxección": "interxección", "numeral": "numeral", "contracción": "contracción", "artigo": "artigo",
    "locución": "locución", "expresión": "locución", "nome propio": "nome propio",
}
# Códigos de categoría de wiktextract (inglés) -> categoría
CATEGORIAS_EN = {"noun": "substantivo", "adj": "adxectivo", "verb": "verbo", "adv": "adverbio", "pron": "pronome",
                 "prep": "preposición", "conj": "conxunción", "intj": "interxección", "num": "numeral",
                 "det": "determinante", "article": "artigo", "name": "nome propio", "phrase": "locución",
                 "contraction": "contracción", "particle": "partícula", "suffix": "sufixo", "prefix": "prefixo"}

MARCA_GALEGO = re.compile(r"^==\s*(?:\{\{-gl-\}\}|\{\{lingua\|gl\}\}|galego|\{\{gl\}\})\s*==\s*$", re.I | re.M)
SECCION = re.compile(r"^(={2,})\s*(.*?)\s*\1\s*$", re.M)

LIMPAR = [
    (re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]"), r"\1"),          # [[ligazón|texto]] -> texto
    (re.compile(r"'{2,}"), ""),                                        # ''cursiva'', '''negra'''
    (re.compile(r"\{\{(?:l|m|w)\|[a-z-]+\|([^|}]+)[^}]*\}\}"), r"\1"),  # {{l|gl|palabra}}
    (re.compile(r"\{\{(?:lb|label|contexto|etiqueta)\|[a-z-]+\|([^}]+)\}\}"), r"(\1)"),  # {{lb|gl|Bot.}}
    (re.compile(r"\{\{[^{}]*\}\}"), ""),                                # calquera outro modelo
    (re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.S), ""),
    (re.compile(r"<[^>]+>"), ""),
    (re.compile(r"\s+"), " "),
]


def limpar(texto: str) -> str:
    for patron, subst in LIMPAR:
        texto = patron.sub(subst, texto)
    return texto.strip(" .;:").strip()


def analizar_pagina_gl(titulo: str, wikitexto: str) -> list[dict]:
    """Entradas galegas dunha páxina do Wiktionary galego."""
    m = MARCA_GALEGO.search(wikitexto)
    if not m:
        return []
    # ata a seguinte sección de nivel 2 (outra lingua)
    resto = wikitexto[m.end():]
    fin = re.search(r"^==[^=].*?==\s*$", resto, re.M)
    texto = resto[: fin.start()] if fin else resto
    entradas = []
    categoria = None
    actual = None
    for liña in texto.splitlines():
        s = SECCION.match(liña)
        if s:
            nome = limpar(s.group(2)).lower()
            nome = re.sub(r"\s+\d+$", "", nome)
            categoria = next((c for n, c in CATEGORIAS_GL.items() if nome.startswith(n)), None)
            actual = None
            continue
        if categoria is None:
            continue
        if liña.startswith("#") and not liña.startswith(("#:", "#*", "##")):
            definicion = limpar(liña.lstrip("#").strip())
            if len(definicion) < 2:
                continue
            if actual is None or actual["categoria"] != categoria:
                actual = {"lema": titulo, "categoria": categoria, "acepcions": []}
                entradas.append(actual)
            actual["acepcions"].append({"definicion": definicion})
        elif liña.startswith(("#:", "#*")) and actual and actual["acepcions"]:
            exemplo = limpar(liña.lstrip("#:*").strip())
            if exemplo:
                actual["acepcions"][-1].setdefault("exemplos", []).append(exemplo)
    return [e for e in entradas if e["acepcions"]]


def procesar_gl(ruta: Path) -> int:
    abrir = bz2.open if ruta.suffix == ".bz2" else open
    n = 0
    with abrir(ruta, "rb") as fh, (SAIDA / "definicions-gl.jsonl").open("w", encoding="utf-8") as saida:
        for _, el in ET.iterparse(fh, events=("end",)):
            if not el.tag.endswith("}page"):
                continue
            ns = el.tag[: el.tag.index("}") + 1]
            titulo = el.findtext(f"{ns}title") or ""
            espazo = el.findtext(f"{ns}ns")
            texto = el.findtext(f"{ns}revision/{ns}text") or ""
            if espazo == "0" and ":" not in titulo:
                for e in analizar_pagina_gl(titulo, texto):
                    e.update({"capa": "definicions-gl", "fontes": ["wiktionary-gl"], "licenza": "CC-BY-SA-4.0",
                              "url": f"https://gl.wiktionary.org/wiki/{titulo}"})
                    saida.write(json.dumps(e, ensure_ascii=False) + "\n")
                    n += 1
            el.clear()
    return n


def analizar_kaikki(obx: dict) -> dict | None:
    """Unha liña de kaikki.org (wiktextract) -> entrada da capa definicions-en."""
    if obx.get("lang_code") != "gl":
        return None
    acepcions = []
    for sentido in obx.get("senses", []):
        glosas = sentido.get("glosses") or sentido.get("raw_glosses")
        if not glosas:
            continue
        a = {"definicion": "; ".join(glosas)}
        etiquetas = [t for t in sentido.get("tags", []) if t not in ("form-of",)]
        if etiquetas:
            a["etiquetas"] = etiquetas
        exemplos = [ex.get("text") for ex in sentido.get("examples", []) if ex.get("text")]
        if exemplos:
            a["exemplos"] = exemplos[:3]
        acepcions.append(a)
    if not acepcions:
        return None
    return {"lema": obx["word"], "categoria": CATEGORIAS_EN.get(obx.get("pos"), obx.get("pos")),
            "capa": "definicions-en", "acepcions": acepcions, "fontes": ["wiktionary-en"],
            "licenza": "CC-BY-SA-4.0", "url": f"https://en.wiktionary.org/wiki/{obx['word']}#Galician"}


def procesar_en(ruta: Path) -> int:
    n = 0
    with ruta.open(encoding="utf-8") as fh, (SAIDA / "definicions-en.jsonl").open("w", encoding="utf-8") as saida:
        for liña in fh:
            e = analizar_kaikki(json.loads(liña))
            if e:
                saida.write(json.dumps(e, ensure_ascii=False) + "\n")
                n += 1
    return n


def descargar() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    for url in (URL_GL, URL_EN):
        destino = CACHE / url.rsplit("/", 1)[1]
        if destino.exists():
            print(f"xa existe {destino}")
            continue
        print(f"descargando {url}")
        peticion = urllib.request.Request(url, headers={"User-Agent": "dicionario-galego (github.com/Xocko12/Dicionario-galego)"})
        with urllib.request.urlopen(peticion) as resposta, destino.open("wb") as fh:
            while bloque := resposta.read(1 << 20):
                fh.write(bloque)


def main() -> None:
    args = sys.argv[1:]
    if "--descargar" in args:
        descargar()
    gl = Path(args[args.index("--gl") + 1]) if "--gl" in args else CACHE / URL_GL.rsplit("/", 1)[1]
    en = Path(args[args.index("--en") + 1]) if "--en" in args else CACHE / URL_EN.rsplit("/", 1)[1]
    SAIDA.mkdir(parents=True, exist_ok=True)
    if gl.exists():
        print(f"definicions-gl.jsonl: {procesar_gl(gl)} entradas")
    else:
        print(f"non hai volcado do Wiktionary galego en {gl} (usa --descargar ou --gl)")
    if en.exists():
        print(f"definicions-en.jsonl: {procesar_en(en)} entradas")
    else:
        print(f"non hai ficheiro de kaikki.org en {en} (usa --descargar ou --en)")


if __name__ == "__main__":
    main()
