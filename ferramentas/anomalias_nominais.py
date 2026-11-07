"""Comproba os plurais dos substantivos e adxectivos coas regras das Normas.

Regras (Normas ortográficas e morfolóxicas, formación do plural):
  - rematados en vogal, ditongo ou -n: engaden -s (casa/casas, lei/leis, can/cans);
  - rematados en -r ou -z: -es (mar/mares, luz/luces);
  - rematados en -s ou -x: os agudos engaden -es (deus/deuses, país/países);
    os graves e esdrúxulos son invariables (lapis, tórax);
  - rematados en -l: monosílabos -les (sol/soles); polisílabos agudos -is
    (papel/papeis, farol/farois, civil/civís, fusil/fusís), agás os compostos dun
    monosílabo, que levan o plural deste (cartafol/cartafoles, chupamel/chupameles:
    revisados en plurais_revisados.tsv); polisílabos graves
    -les (túnel/túneles, fácil/fáciles, réptil/réptiles);
  - rematados noutra consoante (préstamos): -s (club/clubs, chip/chips).

Uso: python3 ferramentas/anomalias_nominais.py [--todas]
Informa dos lemas cuxo plural non segue a regra; os revisados a man están en
datos/correccions/plurais_revisados.tsv.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acentuacion as AC  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
VOGAIS = set("aeiouáéíóúü")


def _co_til(palabra: str, vogal: int | None, nova: str) -> str:
    """Forma nova (sen tiles) coa acentuación recalculada: abrucés + es -> abruceses."""
    if vogal is None:
        return nova
    return AC.acentuar(AC.sen_til(nova), vogal)


def plural_esperado(palabra: str) -> list[str] | None:
    """Plural(es) segundo as Normas, ou None se a regra non decide."""
    if " " in palabra or "-" in palabra or len(palabra) < 2 or not palabra.islower():
        return None
    fin = palabra[-1]
    sil = AC.silabas(palabra)
    n = len(sil)
    vogal = AC.vogal_tonica(palabra)
    aguda = vogal is not None and vogal in sil[-1]
    base = AC.sen_til(palabra)
    if fin in VOGAIS or fin == "n":
        return [palabra + "s"]
    if fin == "z":
        return [_co_til(palabra, vogal, base[:-1] + "ces")]
    if fin == "r":
        return [_co_til(palabra, vogal, base + "es")]
    if fin in "sx":
        return [_co_til(palabra, vogal, base + "es")] if aguda or n == 1 else [palabra]
    if fin == "l":
        # cruel, fiel, dual, biol: vogal + vogal + l son dúas sílabas (cru-el) -> -is
        if n == 1 and len(base) >= 3 and base[-2] in "aeiou" and base[-3] in "aeiou":
            n, aguda = 2, True
        if n == 1:
            return [palabra + "es"]
        if palabra.endswith("bel"):           # amábel -> amábeis (excepción das Normas)
            return [palabra[:-2] + "eis"]
        if aguda:
            if base.endswith("il"):
                return [_co_til(palabra, vogal, base[:-2] + "is")]    # civil -> civís, adaíl -> adaís
            return [_co_til(palabra, vogal, base[:-1] + "is")]        # papel -> papeis
        return [palabra + "es"]                                       # túnel -> túneles, fácil -> fáciles
    return [palabra + "s"]


def buscar(todas: bool = False) -> list[tuple]:
    """Lemas cuxo plural non segue a regra (sen os revisados, salvo todas=True)."""
    return _buscar(todas)


def _buscar(todas: bool) -> list[tuple]:
    ruta_rev = RAIZ / "datos" / "correccions" / "plurais_revisados.tsv"
    revisados = set()
    if ruta_rev.exists():
        revisados = {l.split("\t")[0] for l in ruta_rev.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")}
    problemas = []
    for liña in (RAIZ / "datos" / "lemas.jsonl").open(encoding="utf-8"):
        r = json.loads(liña)
        if r["categoria"] not in ("substantivo", "adxectivo"):
            continue
        if r["lema"] in revisados and not todas:
            continue
        formas = r.get("formas", {})
        for sg, pl in (("ms", "mp"), ("fs", "fp")):
            singulares = formas.get(sg, [])
            obtidos = formas.get(pl, [])
            if not singulares or not obtidos:
                continue
            esperados_por_sg = {x: plural_esperado(x) for x in singulares}
            if any(e is None for e in esperados_por_sg.values()):
                continue
            todos_esperados = {q for e in esperados_por_sg.values() for q in e}
            sobran = [q for q in obtidos if q not in todos_esperados and q not in singulares]
            faltan = [q for q in todos_esperados if q not in obtidos]
            if sobran or faltan:
                problemas.append((r["lema"], singulares, obtidos, sorted(todos_esperados), r["fontes"]))
                break
    return problemas


def main() -> None:
    todas = "--todas" in sys.argv
    problemas = buscar(todas)
    for lema, sg, obt, esp, fontes in problemas[:int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60]:
        print(f"{lema}: {sg} -> {obt} (regra: {esp}) {fontes}")
    print(f"{len(problemas)} plurais fóra da regra{'' if todas else ' (sen revisar)'}")
    sys.exit(1 if problemas and not todas else 0)


if __name__ == "__main__":
    main()
