"""Definicións abertas desde o Wiktionary (CC BY-SA).

Dúas fontes, dúas capas:

  1. O **Wiktionary galego** (gl.wiktionary.org): definicións EN GALEGO, con
     exemplos, sinónimos e antónimos por acepción. Lese do volcado XML:
         https://dumps.wikimedia.org/glwiktionary/latest/glwiktionary-latest-pages-articles.xml.bz2
     -> datos/capas/definicions-gl.jsonl

  2. O **Wiktionary inglés**, entradas galegas, xa procesadas por wiktextract
     (kaikki.org), con definicións en inglés:
         https://kaikki.org/dictionary/Galician/kaikki.org-dictionary-Galician.jsonl
     -> datos/capas/definicions-en.jsonl
     (as entradas de formas flexionadas, «falas: second-person singular of
     falar», non se gardan: a flexión xa a temos)

Uso:
    python3 ferramentas/wiktionary.py --descargar          # baixa os dous ficheiros a fontes/cache/wiktionary/
    python3 ferramentas/wiktionary.py                      # procesa o que haxa en fontes/cache/wiktionary/
    python3 ferramentas/wiktionary.py --gl ficheiro.xml.bz2 --en ficheiro.jsonl

Formato de saída (as dúas capas):
    {"lema": "casa", "categoria": "substantivo", "xenero": "feminino", "capa": "definicions-gl",
     "acepcions": [{"definicion": "...", "exemplos": [...], "sinonimos": [...], "antonimos": [...], "nota": "..."}],
     "fontes": ["wiktionary-gl"], "licenza": "CC-BY-SA-4.0", "url": "https://gl.wiktionary.org/wiki/casa"}

O analizador do Wiktionary galego segue o formato real das páxinas (modelos
{{-gl-}}, {{-substf-|gl}}, {{gl|palabra}}, {{sem|Área}}, {{exemplo|...}},
{{sin|...}}): colle as definicións («# …»), exemplos, sinónimos, antónimos e
notas de cada acepción; o que non recoñece queda fóra, nunca se inventa.
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

# Modelos de sección do Wiktionary galego: {{-substf-|gl}}, {{-verbo-}}...
CATEGORIAS_GL = {
    "subst": "substantivo", "substm": "substantivo", "substf": "substantivo", "substmp": "substantivo",
    "substfp": "substantivo", "substmf": "substantivo", "adx": "adxectivo",
    "verbo": "verbo", "verbot": "verbo", "verboi": "verbo", "verbop": "verbo", "verbopt": "verbo", "verboti": "verbo",
    "adv": "adverbio", "pron": "pronome", "prep": "preposición", "interx": "interxección", "contr": "contracción",
    "conxunc": "conxunción", "art": "artigo", "numcard": "numeral", "numord": "numeral", "num": "numeral",
    "prefixo": "prefixo", "sufixo": "sufixo", "sigla": "sigla", "abrev": "abreviatura",
    "locsm": "locución", "locsf": "locución", "locs": "locución", "locv": "locución", "locadv": "locución",
    "locadx": "locución", "locprep": "locución", "locuc": "locución", "expres": "locución", "expr": "locución",
    "expresrel": "locución", "nomep": "nome propio", "topon": "topónimo", "hidron": "topónimo",
}
XENERO_GL = {"substm": "masculino", "substf": "feminino", "substmp": "masculino", "substfp": "feminino",
             "locsm": "masculino", "locsf": "feminino"}
# Seccións que non son categoría nin lingua; calquera outro {{-xx-}} curto é outra lingua (fin da parte galega)
SECCIONS_GL = {"trad", "relac", "ver", "sin", "ant", "conx", "ref", "var", "obs", "def", "exemplo", "etim", "pron",
               "pronuncia", "son", "hipon", "hiper", "deriv", "nota", "fras", "cit", "imaxe", "cog", "refs"}
# Códigos de categoría de wiktextract (inglés) -> categoría
CATEGORIAS_EN = {"noun": "substantivo", "adj": "adxectivo", "verb": "verbo", "adv": "adverbio", "pron": "pronome",
                 "prep": "preposición", "conj": "conxunción", "intj": "interxección", "num": "numeral",
                 "det": "determinante", "article": "artigo", "name": "nome propio", "phrase": "locución",
                 "contraction": "contracción", "particle": "partícula", "suffix": "sufixo", "prefix": "prefixo"}

INICIO_GL = re.compile(r"\{\{-(?:gl|glref)-(?:\|[^}]*)?\}\}")
SECCION_TPL = re.compile(r"^\{\{-([A-Za-zñ0-9]+)-(?:\|[^}]*)?\}\}")
LIGAZON_GL = re.compile(r"\{\{(gl|Gl|glpt|es|pt|la|ca)\|([^|}]+)(?:\|([^|}]*))?[^}]*\}\}")
CURSIVA = re.compile("'{2,}")


def _texto_ligazon(m: re.Match) -> str:
    texto = m.group(3) or m.group(2)
    if m.group(1) == "Gl":        # Gl = con maiúscula inicial
        texto = texto[:1].upper() + texto[1:]
    return texto


LIMPAR = [
    (LIGAZON_GL, _texto_ligazon),                                          # {{gl|servir|serve}} -> serve
    (re.compile(r"\(\{\{[sS]em\|([^|}]+)[^}]*\}\}\)"), r"(\1)"),          # ({{sem|Zooloxía|gl}}) -> (Zooloxía)
    (re.compile(r"\{\{[sS]em\|([^|}]+)[^}]*\}\}"), r"(\1)"),
    (re.compile(r"\{\{Mai\|([^}]+)\}\}"), lambda m: m.group(1)[:1].upper() + m.group(1)[1:]),
    (re.compile(r"\{\{definicionimpropia\|([^}]*)\}\}"), r"\1"),
    (re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]"), r"\1"),                  # [[ligazón|texto]] -> texto
    (CURSIVA, ""),
    (re.compile(r"\{\{[^{}]*\}\}"), ""),                                    # calquera outro modelo
    (re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.S), ""),
    (re.compile(r"<[^>]+>"), ""),
    (re.compile(r"\s+"), " "),
]


IMAXE = re.compile(r"\[\[(?:File|Ficheiro|Image|Imaxe|Arquivo):[^\]]*(?:\[\[[^\]]*\]\][^\]]*)*\]\]", re.I)
RESTOS = re.compile(r"\{\{|\}\}|\[\[|\]\]|\|\|")


def limpar(texto: str) -> str:
    texto = IMAXE.sub("", texto)
    anterior = None
    while anterior != texto:          # os modelos aniñados límpanse de dentro a fóra
        anterior = texto
        for patron, subst in LIMPAR:
            texto = patron.sub(subst, texto)
    texto = re.sub(r"^\s*(thumb|miniatura|right|left|\d+px)\s*\|?\s*", "", texto)
    return texto.strip(" .;:|").strip()


def ben_limpa(texto: str) -> bool:
    """Sen restos de wikitexto: o que non se dá limpado non entra."""
    return bool(texto) and not RESTOS.search(texto)


def _lista(modelo: str, texto: str) -> list[str]:
    """Palabras dun {{sin|...}}, {{ant|...}}, {{relac|...}}."""
    m = re.search(r"\{\{" + modelo + r"\|(.*)\}\}\s*$", texto.strip())
    if not m:
        return []
    corpo = m.group(1)
    formas = [x.group(2) for x in LIGAZON_GL.finditer(corpo)]
    if not formas:
        formas = [limpar(x) for x in re.split(r"[,;]", corpo)]
    return [f.strip(" .") for f in formas if f.strip(" .")]


def analizar_pagina_gl(titulo: str, wikitexto: str) -> list[dict]:
    """Entradas galegas dunha páxina do Wiktionary galego."""
    m = INICIO_GL.search(wikitexto)
    if not m:
        return []
    texto = wikitexto[m.end():]
    entradas: list[dict] = []
    categoria = None
    xenero = None
    actual = None
    for liña in texto.splitlines():
        s = SECCION_TPL.match(liña.strip())
        if s:
            nome = s.group(1)
            if nome in CATEGORIAS_GL:
                categoria, xenero, actual = CATEGORIAS_GL[nome], XENERO_GL.get(nome), None
                continue
            if nome in SECCIONS_GL or nome in ("gl", "glref"):
                categoria = None          # dentro de trad/relac/ver non hai definicións
                continue
            if len(nome) <= 3 and nome.islower():
                break                     # outra lingua: fin da parte galega
            continue
        if categoria is None:
            continue
        if liña.startswith("#") and not liña.startswith(("#:", "#*", "##")):
            definicion = limpar(liña.lstrip("#").strip())
            if len(definicion) < 2 or not ben_limpa(definicion):
                continue
            if actual is None:
                actual = {"lema": titulo, "categoria": categoria, "acepcions": []}
                if xenero:
                    actual["xenero"] = xenero
                entradas.append(actual)
            actual["acepcions"].append({"definicion": definicion})
        elif liña.startswith(("#:", "#*")) and actual and actual["acepcions"]:
            corpo = liña.lstrip("#:*").strip()
            acepcion = actual["acepcions"][-1]
            ex = re.match(r"\{\{exemplo\|(.*)\}\}\s*$", corpo)
            if ex:
                acepcion.setdefault("exemplos", []).append(limpar(ex.group(1)))
                continue
            for modelo, campo in (("sin", "sinonimos"), ("ant", "antonimos"), ("relac", "relacionadas")):
                lista = _lista(modelo, corpo)
                if lista:
                    acepcion.setdefault(campo, []).extend(x for x in lista if x not in acepcion.get(campo, []))
                    break
            else:
                ob = re.match(r"\{\{obs\|(.*)\}\}\s*$", corpo)
                if ob:
                    acepcion["nota"] = limpar(ob.group(1))
                elif corpo and not corpo.startswith("{{"):
                    acepcion.setdefault("exemplos", []).append(limpar(corpo))
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
        # «falas: second-person singular present of falar» é unha forma, non
        # unha entrada: a flexión xa a temos; só se gardan as acepcións de lemas
        if "form-of" in sentido.get("tags", []) or sentido.get("form_of"):
            continue
        glosas = sentido.get("glosses") or sentido.get("raw_glosses")
        if not glosas:
            continue
        a = {"definicion": "; ".join(glosas)}
        etiquetas = list(sentido.get("tags", []))
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
