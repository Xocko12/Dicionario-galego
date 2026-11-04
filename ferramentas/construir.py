"""Constrúe os produtos derivados en dist/ a partir de datos/.

    python3 ferramentas/construir.py [--kobo]

Saídas:
    dist/dicionario.sqlite            base de datos para calquera ferramenta
    dist/teclado/gl_wordlist.combined lista para teclados AOSP/HeliBoard (dicttool)
    dist/teclado/palabras.tsv         forma<TAB>frecuencia (formato xenérico)
    dist/kobo/galego.tsv              glosario (pyglossary -> Kobo, StarDict...)
    dist/kobo/dicthtml-gl.zip         dicionario Kobo (con --kobo, precisa pyglossary)
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


def formas_do_lema(r: dict, conx: dict):
    """(forma, trazo) de cada forma dun lema."""
    if r["categoria"] == "verbo":
        for forma, clave, persoa in C.formas(conx[r["lema"]]["taboa"]):
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
def construir_sqlite(lemas, conx, frec, nomes, encl) -> None:
    ruta = DIST / "dicionario.sqlite"
    ruta.unlink(missing_ok=True)
    db = sqlite3.connect(ruta)
    db.executescript("""
        CREATE TABLE lemas (id TEXT PRIMARY KEY, lema TEXT NOT NULL, categoria TEXT NOT NULL,
                            xenero TEXT, tipos TEXT, estado TEXT, composicion TEXT,
                            frecuencia INTEGER, fontes TEXT);
        CREATE TABLE formas (forma TEXT NOT NULL, lema_id TEXT NOT NULL REFERENCES lemas(id),
                             trazo TEXT NOT NULL, frecuencia INTEGER);
        CREATE TABLE nomes (nome TEXT PRIMARY KEY);
        CREATE TABLE encliticos (forma TEXT NOT NULL, lema_id TEXT NOT NULL REFERENCES lemas(id),
                                 base TEXT NOT NULL, pronomes TEXT NOT NULL, frecuencia INTEGER);
        CREATE INDEX encliticos_forma ON encliticos(forma);
        CREATE INDEX formas_forma ON formas(forma);
        CREATE INDEX lemas_lema ON lemas(lema);
    """)
    for r in lemas:
        db.execute("INSERT INTO lemas VALUES (?,?,?,?,?,?,?,?,?)", (
            r["id"], r["lema"], r["categoria"], r.get("xenero"),
            ",".join(r.get("tipos", [])) or None, r["estado"],
            "+".join(r["composicion"]) if r.get("composicion") else None,
            r["frecuencia"], ",".join(r["fontes"])))
        db.executemany("INSERT INTO formas VALUES (?,?,?,?)", [
            (forma, r["id"], trazo, frec.get(forma, 0)) for forma, trazo in formas_do_lema(r, conx)])
    db.executemany("INSERT INTO nomes VALUES (?)", [(n,) for n in nomes])
    db.executemany("INSERT INTO encliticos VALUES (?,?,?,?,?)", [
        (r["forma"], f"{r['lema']}#verbo", ",".join(r["base"]), "+".join(r["pronomes"]), r["frecuencia"])
        for r in encl])
    db.commit()
    db.close()


# -- Teclado ----------------------------------------------------------------
def construir_teclado(lemas, conx, frec, nomes, encl) -> int:
    formas: dict[str, int] = {}
    for r in lemas:
        for forma, _ in formas_do_lema(r, conx):
            formas[forma] = frec.get(forma, 0)
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
    partes = [f"<p><b>{html.escape(r['lema'])}</b> <i>{html.escape(r['categoria'].replace('_', ' '))}"]
    if r.get("xenero"):
        partes.append(f" {html.escape(r['xenero'])}")
    if r.get("tipos"):
        partes.append(" (" + ", ".join(html.escape(t) for t in r["tipos"]) + ")")
    if r.get("estado") == "tolerado":
        partes.append(" — forma tolerada")
    partes.append("</i></p>")
    if r.get("composicion"):
        partes.append(f"<p>{html.escape(' + '.join(r['composicion']))}</p>")
    if r["categoria"] == "verbo":
        t = conx[r["lema"]]["taboa"]
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


def construir_glosario(lemas, conx, encl, kobo: bool) -> None:
    saida = DIST / "kobo"
    saida.mkdir(parents=True, exist_ok=True)
    por_lema: dict[str, list[dict]] = {}
    for r in lemas:
        por_lema.setdefault(r["lema"], []).append(r)
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
        destino = saida / "dicthtml-gl.zip"
        destino.unlink(missing_ok=True)
        Glossary().convert(ConvertArgs(
            inputFilename=str(tsv), inputFormat="Tabfile",
            outputFilename=str(destino), outputFormat="Kobo",
            infoOverride={"name": "Dicionario galego aberto", "sourceLang": "gl", "targetLang": "gl"},
        ))


def main() -> None:
    DIST.mkdir(exist_ok=True)
    lemas, conx, frec, nomes, encl = cargar()
    construir_sqlite(lemas, conx, frec, nomes, encl)
    print("dist/dicionario.sqlite")
    n = construir_teclado(lemas, conx, frec, nomes, encl)
    print(f"dist/teclado/: {n} formas")
    construir_glosario(lemas, conx, encl, "--kobo" in sys.argv)
    print("dist/kobo/galego.tsv" + (" e dicthtml-gl.zip" if "--kobo" in sys.argv else ""))


if __name__ == "__main__":
    main()
