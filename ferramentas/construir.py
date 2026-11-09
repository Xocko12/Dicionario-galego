"""Constrúe os produtos derivados en dist/ a partir de datos/.

    python3 ferramentas/construir.py [--kobo]

Saídas:
    dist/dicionario.sqlite            base de datos para calquera ferramenta
    dist/teclado/gl_wordlist.combined lista para teclados AOSP/HeliBoard (dicttool)
    dist/teclado/palabras.tsv         forma<TAB>frecuencia (formato xenérico)
    dist/kobo/galego.tsv              glosario (pyglossary -> Kobo, StarDict...)
    dist/hunspell/gl_ES.dic/.aff      corrector Hunspell (macOS/Pages, LibreOffice, Firefox)
    dist/kobo/dicthtml-gl.zip         dicionario Kobo         (con --kobo, precisa pyglossary)
    dist/stardict/galego.*            StarDict (GoldenDict, apps de dicionario de iOS e Android)
    dist/apple/Galego.apple/          fonte para Dictionary.app de macOS (make nun Mac co Dictionary Development Kit)

Opción --encliticos N (por defecto 600): para os N verbos máis frecuentes
xéranse ademais todas as formas regulares con pronomes enclíticos (díxoma,
díxollelo...), non só as atestadas no corpus. Precisa fontes/cache/ (descargar.py).
Son ~1300 formas por verbo, así que non se gardan en datos/: van ao SQLite,
ao teclado e ao Kobo.
"""

from __future__ import annotations

import html
import json
import math
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conxugacion as C  # noqa: E402
import encliticos  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
DIST = RAIZ / "dist"

NOMES_FORMAS = {"ms": "masculino singular", "fs": "feminino singular",
                "mp": "masculino plural", "fp": "feminino plural"}


def ler_jsonl(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8") as fh:
        return [json.loads(l) for l in fh]


def cargar():
    lemas = ler_jsonl(DATOS / "lemas.jsonl")
    conx = {v["lema"]: v for v in ler_jsonl(DATOS / "conxugacions.jsonl")}
    nomes = [r["nome"] for r in ler_jsonl(DATOS / "nomes.jsonl")]
    encl = ler_jsonl(DATOS / "encliticos.jsonl")
    frec = {}
    for l in (DATOS / "frecuencias.tsv").read_text(encoding="utf-8").splitlines():
        if l.startswith("#"):
            continue
        forma, n = l.rstrip("\n").split("\t")
        frec[forma] = int(n)
    return lemas, conx, frec, nomes, encl


def cargar_capas() -> dict:
    """Capas opcionais, agrupadas polo seu tipo: lexico, siglas, onomastica, codigos; e as locucións."""
    config = json.loads((RAIZ / "fontes" / "capas.json").read_text(encoding="utf-8"))["capas"]
    capas = {"lexico": [], "siglas": [], "onomastica": [], "codigos": [], "locucions": [],
             "semantica": [], "traducions": [], "definicions": []}
    for capa, cfg in config.items():
        ruta = DATOS / "capas" / f"{capa}.jsonl"
        if ruta.exists():
            capas[cfg["tipo"]] += ler_jsonl(ruta)
    ruta = DATOS / "locucions.jsonl"
    if ruta.exists():
        capas["locucions"] = ler_jsonl(ruta)
    capas["sinonimos"] = {}
    ruta = DATOS / "sinonimos.jsonl"
    if ruta.exists():
        for r in ler_jsonl(ruta):
            capas["sinonimos"].setdefault(r["lema"], []).append(r)
    return capas


def formas_do_lema(r: dict, conx: dict):
    """(forma, trazo) de cada forma dun lema."""
    if r["categoria"] == "verbo":
        taboa = r["taboa"] if "taboa" in r else conx[r["lema"]]["taboa"]
        for forma, clave, persoa in C.formas(taboa):
            yield forma, f"{clave}.{persoa}" if persoa else clave
    else:
        vistas = False
        for clave, lista in r.get("formas", {}).items():
            for forma in lista:
                vistas = True
                yield forma, clave
        if not vistas:
            yield r["lema"], ""


# -- SQLite ------------------------------------------------------------------
def construir_sqlite(lemas, conx, frec, nomes, encl, capas) -> None:
    ruta = DIST / "dicionario.sqlite"
    ruta.unlink(missing_ok=True)
    db = sqlite3.connect(ruta)
    db.executescript("""
        CREATE TABLE lemas (id TEXT PRIMARY KEY, lema TEXT NOT NULL, categoria TEXT NOT NULL,
                            xenero TEXT, tipos TEXT, estado TEXT, composicion TEXT,
                            frecuencia INTEGER, fontes TEXT,
                            capa TEXT NOT NULL DEFAULT 'rag');  -- rag = núcleo normativo
        CREATE TABLE locucions (locucion TEXT NOT NULL, categorias TEXT NOT NULL, fontes TEXT);
        CREATE TABLE siglas (forma TEXT NOT NULL, tipo TEXT NOT NULL, nota TEXT, fontes TEXT);
        CREATE TABLE onomastica (nome TEXT NOT NULL, tipo TEXT NOT NULL, capa TEXT NOT NULL, fontes TEXT, nota TEXT);
        CREATE TABLE codigos (codigo TEXT NOT NULL, tipo TEXT NOT NULL, nota TEXT);
        CREATE TABLE sinonimos (lema TEXT NOT NULL, categoria TEXT, sinonimo TEXT NOT NULL, nota TEXT,
                                sinonimo_tolerado INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX sinonimos_lema ON sinonimos(lema);
        CREATE TABLE sentidos (lema TEXT NOT NULL, categoria TEXT, ili TEXT NOT NULL, definicion_en TEXT,
                               sinonimos TEXT, es TEXT, pt TEXT, en TEXT);  -- Galnet / WordNet
        CREATE INDEX sentidos_lema ON sentidos(lema);
        CREATE TABLE traducions (lema TEXT NOT NULL, categoria TEXT, lingua TEXT NOT NULL, traducion TEXT NOT NULL);
        CREATE INDEX traducions_lema ON traducions(lema);
        CREATE TABLE definicions (lema TEXT NOT NULL, categoria TEXT, capa TEXT NOT NULL, n INTEGER NOT NULL,
                                  definicion TEXT NOT NULL, exemplos TEXT, url TEXT);
        CREATE INDEX definicions_lema ON definicions(lema);
        CREATE INDEX siglas_forma ON siglas(forma);
        CREATE INDEX onomastica_nome ON onomastica(nome);
        CREATE TABLE formas (forma TEXT NOT NULL, lema_id TEXT NOT NULL REFERENCES lemas(id),
                             trazo TEXT NOT NULL, frecuencia INTEGER);
        CREATE TABLE nomes (nome TEXT PRIMARY KEY);
        CREATE TABLE encliticos (forma TEXT NOT NULL, lema_id TEXT NOT NULL REFERENCES lemas(id),
                                 base TEXT NOT NULL, pronomes TEXT NOT NULL, frecuencia INTEGER,
                                 orixe TEXT NOT NULL);  -- corpus | sistematica
        CREATE INDEX encliticos_forma ON encliticos(forma);
        CREATE INDEX formas_forma ON formas(forma);
        CREATE INDEX lemas_lema ON lemas(lema);
    """)
    for r in lemas + capas["lexico"]:
        db.execute("INSERT INTO lemas VALUES (?,?,?,?,?,?,?,?,?,?)", (
            r["id"], r["lema"], r["categoria"], r.get("xenero"),
            ",".join(r.get("tipos", [])) or None, r.get("estado"),
            "+".join(r["composicion"]) if r.get("composicion") else None,
            r["frecuencia"], ",".join(r["fontes"]), r.get("capa", "rag")))
        db.executemany("INSERT INTO formas VALUES (?,?,?,?)", [
            (forma, r["id"], trazo, frec.get(forma, 0)) for forma, trazo in formas_do_lema(r, conx)])
    db.executemany("INSERT INTO nomes VALUES (?)", [(n,) for n in nomes])
    db.executemany("INSERT INTO locucions VALUES (?,?,?)",
                   [(r["locucion"], ",".join(r["categorias"]), ",".join(r["fontes"])) for r in capas["locucions"]])
    db.executemany("INSERT INTO siglas VALUES (?,?,?,?)",
                   [(r["forma"], r["tipo"], r.get("nota"), ",".join(r["fontes"])) for r in capas["siglas"]])
    db.executemany("INSERT INTO onomastica VALUES (?,?,?,?,?)",
                   [(r["nome"], r["tipo"], r["capa"], ",".join(r["fontes"]), r.get("nota")) for r in capas["onomastica"]])
    db.executemany("INSERT INTO codigos VALUES (?,?,?)", [(r["codigo"], r["tipo"], r.get("nota")) for r in capas["codigos"]])
    db.executemany("INSERT INTO sentidos VALUES (?,?,?,?,?,?,?,?)", [
        (r["lema"], r["categoria"], x["ili"], x.get("definicion_en"), "|".join(x.get("sinonimos", [])),
         "|".join(x.get("es", [])), "|".join(x.get("pt", [])), "|".join(x.get("en", [])))
        for r in capas["semantica"] for x in r["sentidos"]])
    db.executemany("INSERT INTO traducions VALUES (?,?,?,?)", [
        (r["lema"], r["categoria"], lingua, t)
        for r in capas["traducions"] for lingua in ("es", "pt", "en") for t in r.get(lingua, [])])
    db.executemany("INSERT INTO definicions VALUES (?,?,?,?,?,?,?)", [
        (r["lema"], r["categoria"], r["capa"], n + 1, a["definicion"], "|".join(a.get("exemplos", [])), r.get("url"))
        for r in capas["definicions"] for n, a in enumerate(r["acepcions"])])
    db.executemany("INSERT INTO sinonimos VALUES (?,?,?,?,?)", [
        (r["lema"], r["categoria"], x["forma"], x.get("nota"), int(x.get("non_recomendada", False)))
        for lista in capas["sinonimos"].values() for r in lista for x in r["sinonimos"]])
    db.executemany("INSERT INTO encliticos VALUES (?,?,?,?,?,?)", [
        (r["forma"], f"{r['lema']}#verbo", ",".join(r["base"]), "+".join(r["pronomes"]), r["frecuencia"], r["orixe"])
        for r in encl])
    db.commit()
    db.close()


# -- Teclado ----------------------------------------------------------------
# Capas que van ao corrector Hunspell (as demais son enormes ou traen moito lixo doutras linguas).
CAPAS_CORRECTOR = {"digalego", "comunidade", "terminoloxia", "siglas", "toponimos", "antroponimos"}
# Capas que van ao teclado:
TECLADO_LEXICO = {"digalego", "comunidade", "terminoloxia"}
# nomes propios, tamén as palabras con maiúscula dos nomes compostos (Nova York -> York)
TECLADO_NOMES = {"toponimos", "antroponimos", "cidades", "nomes-outras-linguas"}
# só os nomes dunha soa palabra (iOS, Bayern): os compostos traen palabras xenéricas doutras linguas
TECLADO_NOMES_SIMPLES = {"organizacions", "clubs"}
# só os nomes dunha palabra que veñan destas fontes (persoas con artigo na Wikipedia; non o Wiktionary enteiro)
TECLADO_NOMES_FONTES = {"antroponimos-outras-linguas": {"wikipedia-en", "wikipedia-es", "wikipedia-pt"}}
# Capas de nomes foráneos: un nome que só estea nelas (e non nas galegas nin nos engadidos a man) vai ao
# teclado coa frecuencia mínima, por debaixo de calquera palabra ou nome galego (FORANEO).
TECLADO_FORANEAS = {"cidades", "nomes-outras-linguas", "antroponimos-outras-linguas", "clubs"}
FORANEO = -1

_PALABRA_TECLADO = re.compile(r"^[0-9A-Za-z\u00C0-\u024F\u1E00-\u1EFF][0-9A-Za-z\u00C0-\u024F\u1E00-\u1EFF·'’.&+-]*$")


def _palabra_teclado(p: str) -> bool:
    """Letras latinas e díxitos (polo menos unha letra e dous caracteres) e, dentro, punto medio,
    apóstrofo, punto, guión, & e +. Fóra quedan os símbolos ($, %), as siglas con barras e os
    nomes noutros alfabetos."""
    return len(p) > 1 and any(c.isalpha() for c in p) and bool(_PALABRA_TECLADO.match(p))


def _grafia(p: str) -> int:
    """Entre variantes dun mesmo nome escóllese a grafía máis deliberada: iOS sobre Ios (a illa),
    YouTube sobre Youtube, Maiús sobre MAIÚS, Pol sobre a abreviatura pol."""
    if p.isupper():
        return 0
    if any(c.isupper() for c in p[1:]):
        return 3
    return 2 if p[0].isupper() else 1


def formas_teclado(lemas, conx, frec, nomes, encl, capas) -> dict[str, int]:
    """forma -> frecuencia de todas as palabras do teclado.

    Primeiro as palabras comúns (núcleo, capas léxicas, enclíticos) coa súa frecuencia no
    corpus. Despois os nomes propios e as siglas, pero non os que sexan unha palabra común
    escrita con maiúsculas: «ISO» e «Iso» (a cidade), «SE», «Como», «Paz» ou «A» terían a
    mesma frecuencia ca «iso», «se», «como», «paz» e «a» (o corpus de frecuencias está en
    minúsculas) e os teclados, que buscan sen distinguir maiúsculas, escribían a sigla ou o
    nome no canto da palabra ao deslizar. A maiúscula ponna quen escribe: os teclados AOSP
    aplican á suxestión as maiúsculas que teclea o usuario. As excepcións revisadas a man
    (datos/correccions/teclado.json: «Londres» sobre a forma verbal «londres», «Luís» sobre
    a moeda) entran coa frecuencia do corpus e a palabra común queda con 0.
    Dos nomes compostos (Nova York, Albert Einstein, Santiago de Compostela) entran as
    palabras con maiúscula inicial.
    Os nomes que só veñen das capas foráneas (cidades do mundo, clubs de fóra, nomes doutras
    linguas) e non aparecen no corpus levan FORANEO (-1): a frecuencia mínima do teclado, por
    debaixo das formas galegas sen frecuencia.
    """
    formas: dict[str, int] = {}
    for r in lemas + [r for r in capas["lexico"] if r["capa"] in TECLADO_LEXICO]:
        for forma, _ in formas_do_lema(r, conx):
            formas[forma] = frec.get(forma, 0)
    for r in encl:
        formas.setdefault(r["forma"], r["frecuencia"])
    comuns: dict[str, list[str]] = {}   # minúsculas -> formas comúns con esa grafía
    for f in formas:
        comuns.setdefault(f.lower(), []).append(f)
    ruta = DATOS / "correccions" / "teclado.json"
    mandan = set(json.loads(ruta.read_text(encoding="utf-8"))["nomes"]) if ruta.exists() else set()

    siglas = {r["forma"] for r in capas["siglas"] if r["capa"] == "siglas"}
    candidatos: list[str] = list(siglas)
    candidatos += nomes
    galegos: set[str] = set(candidatos)   # nomes que están nalgunha capa galega ou nos engadidos a man
    for r in capas["onomastica"]:
        capa = r["capa"]
        if " " not in r["nome"]:
            fontes = TECLADO_NOMES_FONTES.get(capa)
            if capa in TECLADO_NOMES or capa in TECLADO_NOMES_SIMPLES or (fontes and fontes & set(r["fontes"])):
                partes = [r["nome"]]
            else:
                continue
        elif capa in TECLADO_NOMES:
            partes = [p for p in r["nome"].split() if p[:1].isupper()]
        else:   # dos compostos das demais capas («Partido Independiente de Osuna») nada
            continue
        # sen siglas con puntos (A.C.CO.) nin códigos (2M1207b): nos nomes son lixo
        partes = [p for p in partes if "." not in p and p[0].isalpha()]
        candidatos += partes
        # os engadidos a man contan como galegos (clubs e persoas que se nomean aquí), agás os nomes doutras linguas
        if capa not in TECLADO_FORANEAS or ("engadidos" in r["fontes"] and capa != "nomes-outras-linguas"):
            galegos.update(partes)
    # entre variantes dun mesmo nome (Pol/POL, NIF/Nif, YouTube/Youtube) escóllese a que máis veces
    # aparece nas capas; en empate, a sigla e logo a grafía máis deliberada (_grafia)
    veces: dict[str, int] = {}
    for p in candidatos:
        veces[p] = veces.get(p, 0) + 1
    propios: dict[str, str] = {}   # minúsculas -> variante escollida
    for p in veces:
        if not _palabra_teclado(p):
            continue
        clave = p.lower()
        if clave in comuns and p not in mandan:
            continue
        actual = propios.get(clave)
        if actual is None or (veces[p], p in siglas, _grafia(p)) > (veces[actual], actual in siglas, _grafia(actual)):
            propios[clave] = p
    for clave, p in propios.items():
        n = frec.get(clave, 0)
        if clave in comuns:   # excepción revisada: o nome manda e a palabra común queda sen frecuencia
            for f in comuns[clave]:
                formas[f] = 0
            n = max(n, 1)
        elif n == 0 and p not in galegos:
            n = FORANEO
        formas[p] = n
    return formas


def construir_teclado(lemas, conx, frec, nomes, encl, capas) -> int:
    formas = formas_teclado(lemas, conx, frec, nomes, encl, capas)
    maximo = max(formas.values()) or 1
    saida = DIST / "teclado"
    saida.mkdir(parents=True, exist_ok=True)

    def escala(n: int) -> int:
        # Escala logarítmica 0-255 do formato AOSP; as formas que non aparecen
        # no corpus (moitas formas verbais) quedan baixas pero presentes (10), e os
        # nomes foráneos sen uso no corpus, no mínimo (1).
        if n == FORANEO:
            return 1
        if n <= 0:
            return 10
        return max(15, min(255, round(255 * math.log(n + 1) / math.log(maximo + 1))))

    orde = sorted(formas.items(), key=lambda x: (-x[1], x[0]))
    with (saida / "gl_wordlist.combined").open("w", encoding="utf-8") as fh:
        fh.write(f"dictionary=main:gl,locale=gl,description=Galego (Dicionario galego aberto),"
                 f"date={int(time.time())},version=1\n")
        for forma, n in orde:
            fh.write(f" word={forma},f={escala(n)}\n")
    with (saida / "palabras.tsv").open("w", encoding="utf-8") as fh:
        for forma, n in orde:
            fh.write(f"{forma}\t{max(n, 0)}\n")
    return len(formas)


# -- Glosario / Kobo ----------------------------------------------------------
def html_lema(r: dict, conx: dict) -> str:
    if "locucion" in r:
        return f"<p><b>{html.escape(r['locucion'])}</b> <i>{html.escape(', '.join(r['categorias']))}</i></p>"
    partes = [f"<p><b>{html.escape(r['lema'])}</b> <i>{html.escape(r['categoria'].replace('_', ' '))}"]
    if r.get("xenero"):
        partes.append(f" {html.escape(r['xenero'])}")
    if r.get("tipos"):
        partes.append(" (" + ", ".join(html.escape(t) for t in r["tipos"]) + ")")
    if r.get("estado") == "tolerado":
        partes.append(" — forma tolerada")
    if r.get("capa") in NOMES_CAPAS:
        partes.append(f" — {NOMES_CAPAS[r['capa']]}, non recollido pola RAG")
    partes.append("</i></p>")
    if r.get("composicion"):
        partes.append(f"<p>{html.escape(' + '.join(r['composicion']))}</p>")
    if r["categoria"] == "verbo":
        t = r["taboa"] if "taboa" in r else conx[r["lema"]]["taboa"]
        partes.append("<table>")
        for clave, nome in C.TEMPOS:
            celas = ["/".join(c) or "—" for c in t[clave]]
            if clave == "imperativo":
                celas = [celas[1], celas[4]]
            partes.append(f"<tr><td><i>{nome}</i></td><td>{html.escape(', '.join(celas))}</td></tr>")
        partes.append(f"<tr><td><i>Xerundio</i></td><td>{html.escape(', '.join(t['xerundio']))}</td></tr>")
        partes.append(f"<tr><td><i>Participio</i></td><td>{html.escape(', '.join(t['participio']))}</td></tr>")
        partes.append("</table>")
    elif len(r.get("formas", {})) > 1 or any(len(v) > 1 for v in r.get("formas", {}).values()):
        partes.append("<p>" + "; ".join(
            f"{NOMES_FORMAS[k]}: {html.escape(', '.join(v))}" for k, v in r["formas"].items()) + "</p>")
    for d in r.get("definicions", []):
        partes.append(f"<p>{html.escape(d)}</p>")
    return "".join(partes)


NOMES_CAPAS = {"digalego": "Digalego", "comunidade": "comunidade", "terminoloxia": "terminoloxía"}


def indice_por_lema(capas: dict) -> None:
    """Índices lema -> rexistros das capas semánticas, para o glosario."""
    for tipo in ("semantica", "traducions", "definicions"):
        indice = {}
        for r in capas[tipo]:
            indice.setdefault(r["lema"], []).append(r)
        capas[tipo + "_por_lema"] = indice


def html_semantica(lema: str, capas: dict) -> str:
    """Definicións (gl, en), traducións e sentidos do WordNet dun lema."""
    partes = []
    for r in capas.get("definicions_por_lema", {}).get(lema, []):
        lingua = "gl" if r["capa"].endswith("-gl") else "en"
        partes.append(f"<p><i>{html.escape(r['categoria'] or '')}</i> <small>(Wiktionary {lingua})</small></p><ol>")
        for a in r["acepcions"]:
            ex = "".join(f"<br/><small>{html.escape(e)}</small>" for e in a.get("exemplos", [])[:2])
            partes.append(f"<li>{html.escape(a['definicion'])}{ex}</li>")
        partes.append("</ol>")
    for r in capas.get("traducions_por_lema", {}).get(lema, []):
        trad = "; ".join(f"<b>{l}</b> {html.escape(', '.join(r[l]))}" for l in ("es", "pt", "en") if r.get(l))
        partes.append(f"<p><i>Trad.</i> ({html.escape(r['categoria'] or '')}): {trad}</p>")
    for r in capas.get("semantica_por_lema", {}).get(lema, []):
        partes.append(f"<p><i>WordNet</i> ({html.escape(r['categoria'] or '')}):</p><ol>")
        for x in r["sentidos"][:8]:
            sin = f" <small>sin. {html.escape(', '.join(x['sinonimos']))}</small>" if x.get("sinonimos") else ""
            partes.append(f"<li>{html.escape(x.get('definicion_en', ''))}{sin}</li>")
        partes.append("</ol>")
    return "".join(partes)


def html_sinonimos(lema: str, capas: dict) -> str:
    partes = []
    for r in capas["sinonimos"].get(lema, []):
        formas = ", ".join(x["forma"] + (f" ({x['nota']})" if x.get("nota") else "")
                           + (" [tolerada]" if x.get("non_recomendada") else "") for x in r["sinonimos"])
        partes.append(f"<p><i>Sin.</i> ({html.escape(r['categoria'])}): {html.escape(formas)}</p>")
    return "".join(partes)


def construir_glosario(lemas, conx, encl, capas, kobo: bool) -> None:
    saida = DIST / "kobo"
    saida.mkdir(parents=True, exist_ok=True)
    indice_por_lema(capas)
    por_lema: dict[str, list[dict]] = {}
    for r in lemas + capas["lexico"]:
        por_lema.setdefault(r["lema"], []).append(r)
    for r in capas["locucions"]:
        por_lema.setdefault(r["locucion"], []).append(r)
    encl_por_lema: dict[str, list[str]] = {}
    for r in encl:
        encl_por_lema.setdefault(r["lema"], []).append(r["forma"])
    tsv = saida / "galego.tsv"
    with tsv.open("w", encoding="utf-8") as fh:
        for lema, rexistros in por_lema.items():
            # As formas flexionadas van como "alternativas": no Kobo, ao tocar
            # "dixeches" ábrese a entrada de "dicir".
            alternativas = []
            for r in rexistros:
                if "locucion" in r:
                    continue
                for forma, _ in formas_do_lema(r, conx):
                    if forma != lema and forma not in alternativas:
                        alternativas.append(forma)
            for forma in encl_por_lema.get(lema, []):     # díxenlle -> dicir
                if forma not in alternativas:
                    alternativas.append(forma)
            cabeceira = "|".join([lema] + alternativas)
            corpo = ("<hr/>".join(html_lema(r, conx) for r in rexistros) + html_sinonimos(lema, capas)
                     + html_semantica(lema, capas))
            corpo = corpo.replace("\t", " ").replace("\r", " ").replace("\n", " ")   # unha liña por entrada
            fh.write(f"{cabeceira}\t{corpo}\n")
    if kobo:
        from pyglossary.glossary_v2 import ConvertArgs, Glossary
        Glossary.init()
        info = {"name": "Dicionario galego aberto", "sourceLang": "gl", "targetLang": "gl",
                "description": "Vocabulario da RAG con flexión e conxugación. GPL-3.0. https://github.com/Xocko12/Dicionario-galego",
                # AppleDict: identificador e créditos do paquete de Dictionary.app
                "CFBundleIdentifier": "gal.dicionario-galego.aberto",
                "copyright": "GPL-3.0 ou posterior. Vocabulario da RAG vía Hunspell-gl (Proxecto Trasno); "
                             "Wiktionary (CC BY-SA), Galnet (CC BY), Apertium (GPL)",
                "author": "Dicionario galego aberto"}
        saidas = [
            (saida / "dicthtml-gl.zip", "Kobo"),                       # Kobo
            (DIST / "stardict" / "galego.ifo", "Stardict"),           # GoldenDict, apps de iOS/Android
            (DIST / "apple" / "Galego.apple", "AppleDict"),           # macOS Dictionary.app (fonte; make nun Mac)
        ]
        for destino, formato in saidas:
            destino.parent.mkdir(parents=True, exist_ok=True)
            if destino.is_dir():
                import shutil
                shutil.rmtree(destino)
            destino.unlink(missing_ok=True)
            Glossary().convert(ConvertArgs(
                inputFilename=str(tsv), inputFormat="Tabfile",
                outputFilename=str(destino), outputFormat=formato, infoOverride=info,
            ))
            if formato == "AppleDict":
                axustar_apple(destino)


def axustar_apple(directorio: Path) -> None:
    """Corrixe a fonte AppleDict de pyglossary para o macOS actual (probado en macOS 27)."""
    import plistlib
    ficheiro = directorio / "Galego_apple.plist"
    plist = plistlib.loads(ficheiro.read_bytes())
    # Con DCSDictionaryXSL ou DCSDictionaryPrefsHTML baleiros, Dictionary Services
    # intenta ler un documento sen nome e o dicionario non se carga.
    for clave in ("DCSDictionaryXSL", "DCSDictionaryPrefsHTML"):
        if not plist.get(clave):
            plist.pop(clave, None)
    plist["CFBundleName"] = "Galego"          # título da sección e da lapela en Dictionary.app
    ficheiro.write_bytes(plistlib.dumps(plist))
    # Formato de paquete 10.11 (datos en Contents/Resources), o que espera o macOS actual.
    makefile = directorio / "Makefile"
    texto = makefile.read_text(encoding="utf-8")
    makefile.write_text(texto.replace("DICT_BUILD_OPTS\t\t=\n", "DICT_BUILD_OPTS\t\t=\t-v 10.11\n", 1),
                        encoding="utf-8")
    # O kit descarta o espazo entre <b>lema</b> e <i>categoría</i>.
    with (directorio / "Galego_apple.css").open("a", encoding="utf-8") as fh:
        fh.write("\n/* dicionario-galego */\np > b + i { margin-left: 0.3em; }\n")


def encliticos_sistematicos(lemas, conx, n_verbos: int) -> list[dict]:
    """Formas regulares con enclíticos dos n_verbos verbos máis frecuentes,
    sen repetir as xa atestadas en datos/encliticos.jsonl."""
    import importar as I
    from hunspell import Hunspell
    mods = I.modulos()
    fonte_de = {str(r): (f, e) for f, e, r in mods}
    h = Hunspell(I.HUNSPELL / "gl.aff", [r for _, _, r in mods])
    verbos = sorted((r for r in lemas if r["categoria"] == "verbo"), key=lambda r: -r["frecuencia"])[:n_verbos]
    fonte_verbo = {r["lema"]: r["fontes"][0] for r in verbos}
    simples = set()
    for r in lemas:
        for forma, _ in formas_do_lema(r, conx):
            simples.add(forma)
    taboas = {lema: v["taboa"] for lema, v in conx.items()}
    return encliticos.sistematicas(
        h, [r["lema"] for r in verbos],
        lambda e, lema: fonte_de.get(e.source, ("",))[0] == fonte_verbo[lema],
        taboas, simples)


def construir_hyphenation() -> None:
    """Patróns de separación silábica, no orixinal (ISO-8859-1) e en UTF-8."""
    orixe = RAIZ / "fontes" / "cache" / "hyph-gl" / "hyph_gl.dic"
    if not orixe.exists():
        return
    destino = DIST / "hyphenation"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "hyph_gl.dic").write_bytes(orixe.read_bytes())
    texto = orixe.read_text(encoding="latin-1").splitlines()
    if texto and texto[0].strip().upper().startswith("ISO8859"):
        texto[0] = "UTF-8"
    (destino / "hyph_gl_utf8.dic").write_text("\n".join(texto) + "\n", encoding="utf-8")
    (destino / "LICENZA.txt").write_text(
        "hyph_gl.dic: patróns de separación silábica do galego, Proxecto Trasno "
        "(extensión de LibreOffice), GPL-3.0-or-later.\n", encoding="utf-8")


def _palabra_limpa(p: str) -> bool:
    """Só letras (con tiles, ñ, ü), punto medio, apóstrofo, punto e guión interiores."""
    return bool(p) and p[0].isalpha() and all(c.isalpha() or c in "·'’.-" for c in p) and " " not in p


def construir_hunspell(lemas, conx, nomes, encl, capas) -> int:
    """dist/hunspell/gl_ES.dic + gl_ES.aff: corrector para macOS (Pages, Mail...),
    LibreOffice, Firefox...

    Estrutura: a mesma ca Hunspell-gl (regras e dicionario de Proxecto Trasno
    cos módulos da RAG, coas nosas correccións ás regras), e por riba:
      - as nosas formas que esa base non recoñece (nomes, topónimos, siglas,
        capas léxicas, formas revisadas coa RAG), como entradas sen afixos;
      - as formas que a base acepta pero que están mal segundo o conxugador da
        RAG ou as Normas, marcadas como prohibidas (FORBIDDENWORD).
    Unha lista plana de 1,3 millóns de formas non cargaba no Hunspell antigo de
    macOS; esta estrutura é a que xa funciona alí."""
    import shutil
    import subprocess

    base_aff = RAIZ / "fontes" / "cache" / "hunspell-gl" / "gl.aff"
    base_dic = RAIZ / "fontes" / "cache" / "hunspell-gl" / "gl.dic"
    if not base_aff.exists():
        print("sen fontes/cache/hunspell-gl: non se constrúe o corrector")
        return 0
    palabras: set[str] = set()
    for r in lemas + [r for r in capas["lexico"] if r["capa"] in CAPAS_CORRECTOR]:
        for forma, _ in formas_do_lema(r, conx):
            palabras.add(forma)
    palabras.update(nomes)
    palabras.update(r["forma"] for r in encl)
    palabras.update(r["forma"] for r in capas["siglas"])
    for r in capas["onomastica"]:
        if r["capa"] in CAPAS_CORRECTOR:
            palabras.update(p for p in r["nome"].split() if p[:1].isupper())
    for r in capas["locucions"]:
        palabras.update(r["locucion"].split())
    palabras = {p for p in palabras if _palabra_limpa(p)}

    # que formas non recoñece xa a base? (hunspell da liña de ordes se o hai; se non, spylls)
    saida = DIST / "hunspell"
    saida.mkdir(parents=True, exist_ok=True)
    lista = saida / "_formas.txt"
    lista.write_text("\n".join(sorted(palabras)) + "\n", encoding="utf-8")
    base = str(base_aff)[:-4]
    hunspell_bin = shutil.which("hunspell")
    # `hunspell -l` parte as palabras polos puntos (D.ª, S.A.R): esas compróbanse sempre con spylls
    con_punto = {p for p in palabras if "." in p} if hunspell_bin else palabras
    if hunspell_bin:
        lista.write_text("\n".join(sorted(palabras - con_punto)) + "\n", encoding="utf-8")
        # ruta completa: co PATH mínimo de abaixo non se atopa o de Homebrew (/opt/homebrew/bin)
        res = subprocess.run([hunspell_bin, "-i", "utf-8", "-d", base, "-l"], input=lista.read_bytes(),
                             capture_output=True, env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": "/usr/bin:/bin"})
        # só formas enteiras da lista, nunca anacos que hunspell separase
        adicions = set(res.stdout.decode("utf-8").split()) & palabras
    else:
        adicions = set()
    if con_punto:
        from spylls.hunspell import Dictionary
        d = Dictionary.from_files(base)
        adicions |= {p for p in con_punto if not d.lookup(p)}
    lista.unlink()

    import prohibidas as P
    prohibidas = P.calcular(lemas, conx, encl)
    prohibidas.update({hun: lema for hun, cor, lema, _ in encliticos.CORRECCIONS_TIL if hun not in palabras})
    prohibidas = {f: l for f, l in prohibidas.items() if f not in palabras and _palabra_limpa(f)}

    FLAG = "997"
    aff = base_aff.read_text(encoding="utf-8").rstrip("\n") + f"\nFORBIDDENWORD {FLAG}\n"
    (saida / "gl_ES.aff").write_text(aff, encoding="utf-8")
    entradas = [l for l in base_dic.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
    entradas += sorted(adicions)
    entradas += [f"{f}/{FLAG}" for f in sorted(prohibidas)]
    with (saida / "gl_ES.dic").open("w", encoding="utf-8") as fh:
        fh.write(f"{len(entradas)}\n" + "\n".join(entradas) + "\n")
    with (saida / "prohibidas.tsv").open("w", encoding="utf-8") as fh:
        fh.write("# forma que Hunspell-gl acepta\tverbo\n")
        for f, l in sorted(prohibidas.items()):
            fh.write(f"{f}\t{l}\n")
    (saida / "LEME.txt").write_text(
        "Corrector ortográfico galego (Dicionario galego aberto, GPL-3.0).\n\n"
        "macOS (Pages, Mail, Safari...): copiar gl_ES.dic e gl_ES.aff a ~/Library/Spelling/ (crear o cartafol se non existe),\n"
        "pechar e abrir as aplicacións e escoller «Galego» en Axustes do Sistema > Teclado > Ortografía (ou Editar > Ortografía).\n"
        "Se xa había outro gl_ES.dic/.aff nese cartafol, substituílo (só pode haber un par por lingua).\n"
        "LibreOffice: Ferramentas > Opcións > Configuración de idioma; ou copiar a ~/.config/libreoffice/4/user/wordbook/.\n\n"
        "Estrutura: regras e dicionario de Hunspell-gl (Proxecto Trasno, módulos da RAG, coas correccións ás regras\n"
        f"de fontes/parches.json) + {len(adicions)} formas engadidas (nomes, topónimos, siglas, capas léxicas, formas\n"
        f"revisadas co conxugador da RAG) + {len(prohibidas)} formas prohibidas (as que Hunspell-gl acepta pero están mal\n"
        "segundo o conxugador da RAG ou as Normas: ver prohibidas.tsv).\n", encoding="utf-8")
    print(f"dist/hunspell/: {len(entradas)} entradas ({len(adicions)} engadidas, {len(prohibidas)} prohibidas)")
    return len(entradas)


def main() -> None:
    DIST.mkdir(exist_ok=True)
    construir_hyphenation()
    lemas, conx, frec, nomes, encl = cargar()
    capas = cargar_capas()
    n_verbos = 600
    if "--encliticos" in sys.argv:
        n_verbos = int(sys.argv[sys.argv.index("--encliticos") + 1])
    for r in encl:
        r["orixe"] = "corpus"
    if n_verbos:
        xa = {(r["forma"], r["lema"], tuple(r["pronomes"])) for r in encl}
        novas = [r for r in encliticos_sistematicos(lemas, conx, n_verbos)
                 if (r["forma"], r["lema"], tuple(r["pronomes"])) not in xa]
        for r in novas:
            r["orixe"] = "sistematica"
        encl += novas
        print(f"enclíticos: {len(encl) - len(novas)} do corpus + {len(novas)} sistemáticas ({n_verbos} verbos)")
        with (DIST / "encliticos_corrixidos.tsv").open("w", encoding="utf-8") as fh:
            fh.write("# Formas con enclíticos nas que se corrixiu o til de Hunspell-gl (para comunicar a Trasno)\n")
            fh.write("# hunspell\tcorrixida\tverbo\tforma base\n")
            for hun, cor, lema, base in sorted(set(encliticos.CORRECCIONS_TIL)):
                fh.write(f"{hun}\t{cor}\t{lema}\t{base}\n")
        print(f"tiles corrixidos: {len(set(encliticos.CORRECCIONS_TIL))} (dist/encliticos_corrixidos.tsv)")
    construir_sqlite(lemas, conx, frec, nomes, encl, capas)
    print("dist/dicionario.sqlite")
    n = construir_teclado(lemas, conx, frec, nomes, encl, capas)
    construir_hunspell(lemas, conx, nomes, encl, capas)
    print(f"dist/teclado/: {n} formas")
    construir_glosario(lemas, conx, encl, capas, "--kobo" in sys.argv)
    print("dist/kobo/galego.tsv" + (" + Kobo, StarDict e AppleDict" if "--kobo" in sys.argv else ""))


if __name__ == "__main__":
    main()
