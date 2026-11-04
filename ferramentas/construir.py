"""Constrúe os produtos derivados en dist/ a partir de datos/.

    python3 ferramentas/construir.py [--kobo]

Saídas:
    dist/dicionario.sqlite            base de datos para calquera ferramenta
    dist/teclado/gl_wordlist.combined lista para teclados AOSP/HeliBoard (dicttool)
    dist/teclado/palabras.tsv         forma<TAB>frecuencia (formato xenérico)
    dist/kobo/galego.tsv              glosario (pyglossary -> Kobo, StarDict...)
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


def cargar():
    lemas = [json.loads(l) for l in (DATOS / "lemas.jsonl").open(encoding="utf-8")]
    conx = {}
    for l in (DATOS / "conxugacions.jsonl").open(encoding="utf-8"):
        v = json.loads(l)
        conx[v["lema"]] = v
    nomes = [json.loads(l)["nome"] for l in (DATOS / "nomes.jsonl").open(encoding="utf-8")]
    encl = [json.loads(l) for l in (DATOS / "encliticos.jsonl").open(encoding="utf-8")]
    frec = {}
    for l in (DATOS / "frecuencias.tsv").open(encoding="utf-8"):
        if l.startswith("#"):
            continue
        forma, n = l.rstrip("\n").split("\t")
        frec[forma] = int(n)
    return lemas, conx, frec, nomes, encl


def cargar_capas() -> dict:
    """Capas opcionais, agrupadas polo seu tipo: lexico, siglas, onomastica, codigos; e as locucións."""
    config = json.loads((RAIZ / "fontes" / "capas.json").read_text(encoding="utf-8"))["capas"]
    capas = {"lexico": [], "siglas": [], "onomastica": [], "codigos": [], "locucions": []}
    for capa, cfg in config.items():
        ruta = DATOS / "capas" / f"{capa}.jsonl"
        if ruta.exists():
            capas[cfg["tipo"]] += [json.loads(l) for l in ruta.open(encoding="utf-8")]
    ruta = DATOS / "locucions.jsonl"
    if ruta.exists():
        capas["locucions"] = [json.loads(l) for l in ruta.open(encoding="utf-8")]
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
    db.executemany("INSERT INTO encliticos VALUES (?,?,?,?,?,?)", [
        (r["forma"], f"{r['lema']}#verbo", ",".join(r["base"]), "+".join(r["pronomes"]), r["frecuencia"], r["orixe"])
        for r in encl])
    db.commit()
    db.close()


# -- Teclado ----------------------------------------------------------------
# Capas que van ao teclado (as demais son enormes ou nomes doutras linguas).
CAPAS_TECLADO = {"digalego", "comunidade", "terminoloxia", "siglas", "toponimos", "antroponimos"}


def construir_teclado(lemas, conx, frec, nomes, encl, capas) -> int:
    formas: dict[str, int] = {}
    for r in lemas + [r for r in capas["lexico"] if r["capa"] in CAPAS_TECLADO]:
        for forma, _ in formas_do_lema(r, conx):
            formas[forma] = frec.get(forma, 0)
    for r in capas["siglas"]:
        if r["capa"] in CAPAS_TECLADO:
            formas.setdefault(r["forma"], frec.get(r["forma"].lower(), 0))
    for r in capas["onomastica"]:
        if r["capa"] in CAPAS_TECLADO and " " not in r["nome"]:
            formas.setdefault(r["nome"], frec.get(r["nome"].lower(), 0))
    for nome in nomes:
        formas.setdefault(nome, frec.get(nome.lower(), 0))
    for r in encl:
        formas.setdefault(r["forma"], r["frecuencia"])
    maximo = max(formas.values()) or 1
    saida = DIST / "teclado"
    saida.mkdir(parents=True, exist_ok=True)

    def escala(n: int) -> int:
        # Escala logarítmica 0-255 do formato AOSP; as formas que non aparecen
        # no corpus (moitas formas verbais) quedan baixas pero presentes.
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
            fh.write(f"{forma}\t{n}\n")
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


def construir_glosario(lemas, conx, encl, capas, kobo: bool) -> None:
    saida = DIST / "kobo"
    saida.mkdir(parents=True, exist_ok=True)
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
            corpo = "<hr/>".join(html_lema(r, conx) for r in rexistros)
            fh.write(f"{cabeceira}\t{corpo}\n")
    if kobo:
        from pyglossary.glossary_v2 import ConvertArgs, Glossary
        Glossary.init()
        info = {"name": "Dicionario galego aberto", "sourceLang": "gl", "targetLang": "gl",
                "description": "Vocabulario da RAG con flexión e conxugación. GPL-3.0. https://github.com/Xocko12/Dicionario-galego"}
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


def main() -> None:
    DIST.mkdir(exist_ok=True)
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
    print(f"dist/teclado/: {n} formas")
    construir_glosario(lemas, conx, encl, capas, "--kobo" in sys.argv)
    print("dist/kobo/galego.tsv" + (" + Kobo, StarDict e AppleDict" if "--kobo" in sys.argv else ""))


if __name__ == "__main__":
    main()
