"""Compara as nosas táboas de conxugación coas do conxugador da RAG.

O sitio da RAG (academia.gal) non se pode consultar automaticamente desde
aquí, así que o fluxo é manual: cópiase a táboa do conxugador tal como se
presenta na web (seleccionar e pegar) nun ficheiro docs/rag/<verbo>.txt e
execútase:

    python3 ferramentas/comparar_rag.py docs/rag/            # informa das diferenzas
    python3 ferramentas/comparar_rag.py --aceptar docs/rag/  # e garda as táboas da RAG
                                                             # en datos/correccions/referencia.json

Despois de --aceptar hai que executar importar.py (e capas.py) para que a
referencia se aplique aos datos.

Formato que se espera (o que sae ao pegar o conxugador):

    Presente        P.Pluscuamperfecto
        provexo         provera
        ...
    Pretérito imperfecto    Futuro
    ...
    Subxuntivo
        Presente
        provexa ...
    Imperativo
        -
        prové
    Infinitivo Conx.
    Xerundio
    Participio
        provido/provisto
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conxugacion as C  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

# Nomes do conxugador da RAG -> claves nosas (indicativo por defecto)
NOMES_RAG = {
    "presente": "indicativo.presente",
    "pretérito imperfecto": "indicativo.copreterito",
    "pretérito perfecto": "indicativo.preterito",
    "p.pluscuamperfecto": "indicativo.antepreterito",
    "pluscuamperfecto": "indicativo.antepreterito",
    "futuro": "indicativo.futuro",
    "condicional": "indicativo.pospreterito",
    "imperativo": "imperativo",
    "infinitivo conx.": "infinitivo.conxugado",
    "infinitivo conxugado": "infinitivo.conxugado",
    "xerundio": "xerundio",
    "participio": "participio",
}
SUBXUNTIVO = {"indicativo.presente": "subxuntivo.presente", "indicativo.copreterito": "subxuntivo.preterito",
              "indicativo.futuro": "subxuntivo.futuro"}
TAMAÑOS = {"xerundio": 1, "participio": 4}


def _nome(texto: str) -> str | None:
    return NOMES_RAG.get(texto.strip().lower().rstrip(":"))


def analizar(texto: str) -> dict:
    """Converte o texto pegado do conxugador nunha táboa coas nosas claves."""
    liñas = [l.strip() for l in texto.splitlines() if l.strip()]
    taboa: dict = {}
    modo_subx = False
    i = 0
    while i < len(liñas):
        partes = [p.strip() for p in re.split(r"\t+|\s{2,}", liñas[i]) if p.strip()]
        if len(partes) == 1 and partes[0].lower() in ("indicativo", "subxuntivo"):
            modo_subx = partes[0].lower() == "subxuntivo"
            i += 1
            continue
        claves = [_nome(p) for p in partes]
        if not claves or any(c is None for c in claves):
            i += 1
            continue
        if modo_subx:
            claves = [SUBXUNTIVO.get(c, c) for c in claves]
        n = max(TAMAÑOS.get(c, 6) for c in claves)
        filas = []
        for j in range(i + 1, min(i + 1 + n, len(liñas))):
            celas = [p.strip() for p in re.split(r"\t+|\s{2,}", liñas[j]) if p.strip()]
            if len(celas) < len(claves) or any(_nome(c) for c in celas):
                break
            filas.append(celas)
        for k, clave in enumerate(claves):
            valores = [f[k] for f in filas]
            if clave in TAMAÑOS:
                formas = [v for v in valores if v != "-"]
                taboa[clave] = [x.strip() for v in formas for x in v.split("/")]
            else:
                taboa[clave] = [[] if v == "-" else [x.strip() for x in v.split("/")] for v in valores]
                taboa[clave] += [[]] * (6 - len(taboa[clave]))
        i += 1 + len(filas)
    if "participio" in taboa and len(taboa["participio"]) == 4:
        # a RAG lista m.sg, f.sg, m.pl, f.pl; nós m.sg, m.pl, f.sg, f.pl
        p = taboa["participio"]
        taboa["participio"] = [p[0], p[2], p[1], p[3]]
    return taboa


def cargar_nosas() -> dict[str, dict]:
    taboas = {}
    for ruta in [RAIZ / "datos" / "conxugacions.jsonl"] + sorted((RAIZ / "datos" / "capas").glob("*.jsonl")):
        for liña in ruta.open(encoding="utf-8"):
            r = json.loads(liña)
            if "taboa" in r:
                taboas.setdefault(r["lema"], r["taboa"])
    return taboas


def comparar(lema: str, rag: dict, nosa: dict) -> list[str]:
    diferenzas = []
    for clave, valor in rag.items():
        if clave in TAMAÑOS:
            if set(valor) != set(nosa.get(clave, [])):
                diferenzas.append(f"{clave}: RAG {valor} / nós {nosa.get(clave)}")
            continue
        for p, cela in enumerate(valor):
            if clave == "imperativo" and p not in (1, 3, 4):
                continue
            nosa_cela = nosa.get(clave, [[]] * 6)[p]
            if set(cela) != set(nosa_cela):
                diferenzas.append(f"{clave}.{C.PERSOAS[p]}: RAG {cela} / nós {nosa_cela}")
    return diferenzas


def main() -> None:
    aceptar = "--aceptar" in sys.argv
    rutas = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    ficheiros = [f for r in rutas for f in (sorted(r.glob("*.txt")) if r.is_dir() else [r])]
    if not ficheiros:
        print(__doc__)
        sys.exit(2)
    nosas = cargar_nosas()
    ref_ruta = RAIZ / "datos" / "correccions" / "referencia.json"
    referencia = json.loads(ref_ruta.read_text(encoding="utf-8"))
    total = 0
    for f in ficheiros:
        lema = f.stem
        rag = analizar(f.read_text(encoding="utf-8"))
        if not rag:
            print(f"{lema}: non se puido interpretar o ficheiro")
            continue
        if lema not in nosas:
            print(f"{lema}: non está nas nosas táboas")
            continue
        difs = comparar(lema, rag, nosas[lema])
        total += len(difs)
        print(f"{lema}: {len(rag)} tempos lidos, {len(difs)} diferenzas")
        for d in difs:
            print("   ", d)
        if aceptar:
            referencia[lema] = {"nota": "Táboa do conxugador da RAG (comparar_rag.py --aceptar).", "celas": rag}
    if aceptar:
        ref_ruta.write_text(json.dumps(referencia, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"referencia.json actualizado con {len(ficheiros)} verbos; executa importar.py e capas.py")
    sys.exit(1 if total and not aceptar else 0)


if __name__ == "__main__":
    main()
