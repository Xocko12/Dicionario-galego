"""Definicións abertas desde o Wiktionary (CC BY-SA).

Dúas fontes, dúas capas:

  1. O **Wiktionary galego** (gl.wiktionary.org): definicións EN GALEGO, con
     exemplos, sinónimos e antónimos por acepción. Lese do volcado XML:
         https://dumps.wikimedia.org/glwiktionary/latest/glwiktionary-latest-pages-articles.xml.bz2
     -> datos/capas/definicions-gl.jsonl

  2. O **Wiktionary inglés**, entradas galegas, xa procesadas por wiktextract
     (kaikki.org). As súas glosas están en inglés e aquí non se gardan en
     inglés: pasan a galego coa táboa datos/traducions/definicions-wiktionary.tsv
     e cunhas poucas regras, e só entran as acepcións que a capa definicions-gl
     non dá xa (as palabras que lle faltan e as acepcións que lle faltan):
         https://kaikki.org/dictionary/Galician/kaikki.org-dictionary-Galician.jsonl
     -> datos/capas/definicions-traducidas.jsonl
     (as entradas de formas flexionadas, «falas: second-person singular of
     falar», non se gardan: a flexión xa a temos)

Uso:
    python3 ferramentas/wiktionary.py --descargar          # baixa os dous ficheiros a fontes/cache/wiktionary/
    python3 ferramentas/wiktionary.py                      # procesa o que haxa en fontes/cache/wiktionary/
    python3 ferramentas/wiktionary.py --gl ficheiro.xml.bz2 --en ficheiro.jsonl

Formato de saída (as dúas capas; a traducida leva ademais «etiquetas» por acepción):
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
import hashlib
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "fontes" / "cache" / "wiktionary"
SAIDA = RAIZ / "datos" / "capas"
TRADUCIONS = RAIZ / "datos" / "traducions" / "definicions-wiktionary.tsv"

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
    """Unha liña de kaikki.org (wiktextract) -> entrada intermedia, coas glosas
    aínda en inglés. Non se garda: pasa por traducir_entrada."""
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
            "acepcions": acepcions, "url": f"https://en.wiktionary.org/wiki/{obx['word']}#Galician"}


# --- Do inglés ao galego -----------------------------------------------------
#
# Neste repositorio non se gardan definicións en inglés. As glosas do Wiktionary
# inglés pasan a galego por dúas vías: as de fórmula fixa («a parish of Samos,
# Lugo, Galicia») tradúcense con regras; as demais, coa táboa
# datos/traducions/definicions-wiktionary.tsv (lema, categoría, clave da glosa,
# definición en galego). A clave é un resumo SHA-1 da glosa inglesa, para non
# ter que gardar o texto inglés. O que non ten tradución queda fóra.

# Formas flexionadas que wiktextract non marca como tales
FORMA_EN = re.compile(r"^(?:(?:first|second|third)-person|inflection of|plural of|feminine (?:singular|plural) of|"
                      r"masculine plural of|past participle of|gerund of)\b.* of [^ ]+$")
REMITE_EN = [(re.compile(r"^reintegrationist spelling of ([^;:(,]+)$"), "Grafía reintegracionista de {}"),
             (re.compile(r"^alternative form of ([^;:(,]+)$"), "Forma alternativa de {}"),
             (re.compile(r"^alternative spelling of ([^;:(,]+)$"), "Grafía alternativa de {}")]
LUGAR_EN = re.compile(r"^a (?:village|locality) in ([^;:(,]+) parish, ([^;:(,]+), ([^;:(,]+), Galicia(?:, Spain)?$")
PARROQUIA_EN = re.compile(r"^a parish of ([^;:(,]+), ([^;:(,]+), Galicia(?:, Spain)?$")

ETIQUETAS_EN = {
    "transitive": "transitivo", "intransitive": "intransitivo", "ambitransitive": "transitivo e intransitivo",
    "ditransitive": "ditransitivo", "pronominal": "pronominal", "reflexive": "reflexivo", "impersonal": "impersoal",
    "auxiliary": "auxiliar", "copulative": "copulativo", "uncountable": "incontable", "countable": "contable",
    "invariable": "invariable", "indeclinable": "invariable", "plural-only": "só en plural", "in-plural": "en plural",
    "plural-normally": "normalmente en plural", "collective": "colectivo", "archaic": "arcaico", "dated": "anticuado",
    "obsolete": "obsoleto", "historical": "histórico", "figuratively": "figurado", "broadly": "por extensión",
    "metonymically": "por metonimia", "idiomatic": "idiomático", "derogatory": "pexorativo", "vulgar": "vulgar",
    "offensive": "ofensivo", "slur": "ofensivo", "colloquial": "coloquial", "informal": "informal",
    "familiar": "familiar", "formal": "formal", "literary": "literario", "poetic": "poético", "slang": "xerga",
    "regional": "rexional", "dialectal": "dialectal", "rare": "raro", "uncommon": "pouco usado",
    "humorous": "humorístico", "sarcastic": "sarcástico", "euphemistic": "eufemístico", "childish": "infantil",
    "endearing": "afectivo", "affective": "afectivo", "proscribed": "non normativo", "nonstandard": "non normativo",
    "misspelling": "grafía errada", "neologism": "neoloxismo", "abbreviation": "abreviatura", "initialism": "sigla",
    "acronym": "acrónimo", "clipping": "acurtamento", "contraction": "contracción", "relational": "relacional",
    "Internet": "Internet",
}
CATEGORIAS_EN.update({"proverb": "refrán", "prep_phrase": "locución", "character": "letra"})
GLOSA_NO_EXEMPLO = re.compile(r"\s*\(“[^”]*”\)")


def clave_glosa(glosa: str) -> str:
    """Clave dunha glosa inglesa na táboa de traducións (SHA-1 abreviado)."""
    return hashlib.sha1(glosa.encode("utf-8")).hexdigest()[:10]


def _de(nome: str) -> str:
    """«de» + nome de lugar, coa contracción do artigo: do Corgo, da Estrada."""
    for artigo, contraccion in (("O ", "do "), ("A ", "da "), ("Os ", "dos "), ("As ", "das ")):
        if nome.startswith(artigo):
            return contraccion + nome[len(artigo):]
    return "de " + nome


def traducir_por_regra(glosa: str) -> str | None:
    """Glosas de fórmula fixa -> galego. '' = forma flexionada (non se garda); None = sen regra."""
    glosa = " ".join(glosa.split())
    if FORMA_EN.match(glosa):
        return ""
    for patron, modelo in REMITE_EN:
        if m := patron.match(glosa):
            return modelo.format(m.group(1))
    if m := LUGAR_EN.match(glosa):
        return f"Lugar da parroquia {_de(m.group(1))}, no concello {_de(m.group(2))}, na provincia {_de(m.group(3))}"
    if m := PARROQUIA_EN.match(glosa):
        return f"Parroquia do concello {_de(m.group(1))}, na provincia {_de(m.group(2))}"
    return None


def ler_traducions(ruta: Path = TRADUCIONS) -> dict[tuple[str, str, str], str]:
    traducions = {}
    if ruta.exists():
        with ruta.open(encoding="utf-8") as fh:
            for liña in fh:
                campos = liña.rstrip("\n").split("\t")
                if len(campos) == 4 and not liña.startswith("#"):
                    traducions[tuple(campos[:3])] = campos[3]
    return traducions


def _normal(definicion: str) -> str:
    """Para comparar definicións: sen a marca de ámbito inicial, sen puntuación nin maiúsculas."""
    definicion = definicion.strip()
    while definicion.startswith("("):          # (Zooloxía) …, ((Hostalería), (Alimentación)) …
        resto = re.sub(r"^\(+[^()]*\)+[\s,]*", "", definicion)
        if resto == definicion:
            break
        definicion = resto
    return re.sub(r"[^\w ]", "", definicion.lower()).strip()


def definicions_existentes(ruta: Path | None = None) -> dict[str, set[str]]:
    """lema -> definicións (normalizadas) que xa dá a capa definicions-gl."""
    ruta = ruta or SAIDA / "definicions-gl.jsonl"
    existentes: dict[str, set[str]] = {}
    if ruta.exists():
        with ruta.open(encoding="utf-8") as fh:
            for liña in fh:
                r = json.loads(liña)
                existentes.setdefault(r["lema"], set()).update(_normal(a["definicion"]) for a in r["acepcions"])
    return existentes


def traducir_entrada(e: dict, traducions: dict, existentes: dict[str, set[str]]) -> dict | None:
    """Entrada intermedia (glosas en inglés) -> entrada da capa definicions-traducidas, en galego.
    Quedan fóra as acepcións sen tradución e as que repiten unha definición que
    xa está na capa definicions-gl ou na propia entrada."""
    vistas = set(existentes.get(e["lema"], ()))
    acepcions = []
    for a in e["acepcions"]:
        definicion = traducions.get((e["lema"], e["categoria"], clave_glosa(a["definicion"])))
        if definicion is None:
            definicion = traducir_por_regra(a["definicion"])
        if not definicion or _normal(definicion) in vistas:
            continue
        vistas.add(_normal(definicion))
        nova = {"definicion": definicion}
        etiquetas = list(dict.fromkeys(ETIQUETAS_EN[t] for t in a.get("etiquetas", []) if t in ETIQUETAS_EN))
        if etiquetas:
            nova["etiquetas"] = etiquetas
        # o exemplo é a primeira liña; as seguintes son a súa tradución ao inglés
        exemplos = [GLOSA_NO_EXEMPLO.sub("", x.split("\n")[0]).strip() for x in a.get("exemplos", [])]
        exemplos = [x for x in exemplos if x and "“" not in x]
        if exemplos:
            nova["exemplos"] = exemplos
        acepcions.append(nova)
    if not acepcions:
        return None
    return {"lema": e["lema"], "categoria": e["categoria"], "capa": "definicions-traducidas", "acepcions": acepcions,
            "fontes": ["wiktionary-en"], "licenza": "CC-BY-SA-4.0", "url": e["url"]}


def procesar_en(ruta: Path) -> int:
    traducions = ler_traducions()
    existentes = definicions_existentes()
    n = 0
    with ruta.open(encoding="utf-8") as fh, (SAIDA / "definicions-traducidas.jsonl").open("w", encoding="utf-8") as saida:
        for liña in fh:
            e = analizar_kaikki(json.loads(liña))
            e = e and traducir_entrada(e, traducions, existentes)
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
        print(f"definicions-traducidas.jsonl: {procesar_en(en)} entradas")
    else:
        print(f"non hai ficheiro de kaikki.org en {en} (usa --descargar ou --en)")


if __name__ == "__main__":
    main()
