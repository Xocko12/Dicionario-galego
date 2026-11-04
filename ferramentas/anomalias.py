"""Busca formas verbais que non seguen os patróns xerais do galego.

Non todas son erros (os verbos irregulares teñen as súas excepcións), pero
cada anomalía hai que revisala. Uso: python3 ferramentas/anomalias.py
"""

import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def sen_til(p):
    return "".join(c for c in unicodedata.normalize("NFD", p) if unicodedata.category(c) != "Mn").replace("ñ", "ñ")


def sen_til_agudo(p):
    """Quita só os tiles agudos (non o ñ nin a diérese)."""
    nfd = unicodedata.normalize("NFD", p)
    return unicodedata.normalize("NFC", nfd.replace("́", ""))


# subxuntivo que non sae do presente P1 (poida, queira, provexa) — revisados
IRREGULARES_SUBXUNTIVO = {"poder", "querer", "prover", "desprover"}


def comprobacions(lema, t):
    inf = lema
    raiz = sen_til_agudo(inf)          # oír -> oir, pór -> por
    base = inf[:-1]                    # fala-, come-, oí-
    esperado = {
        ("imperativo", 4): [base + "de"],
        ("xerundio", None): [base + "ndo"],
        ("indicativo.presente", 3): [base + "mos"],
        ("indicativo.presente", 4): [base + "des"],
        ("indicativo.futuro", 0): [raiz + "ei"],
        ("indicativo.futuro", 5): [raiz + "án"],
        ("indicativo.pospreterito", 0): [raiz + "ía"],
        ("indicativo.pospreterito", 3): [raiz + "iamos"],
        ("infinitivo.conxugado", 1): [inf + "es"],
        ("infinitivo.conxugado", 3): [inf + "mos"],
    }
    for (clave, p), formas in esperado.items():
        cela = t[clave] if p is None else t[clave][p]
        if not cela:
            continue
        if not any(f in cela for f in formas):
            yield f"{clave}{'' if p is None else '.P' + str(p + 1)}", cela, formas
    # terminacións
    fins = {
        ("indicativo.presente", 1): ("s",), ("indicativo.presente", 5): ("n",),
        ("indicativo.preterito", 1): ("ches",), ("indicativo.preterito", 4): ("stes",),
        ("indicativo.preterito", 5): ("ron",), ("indicativo.copreterito", 3): ("amos",),
        ("subxuntivo.presente", 3): ("mos",), ("subxuntivo.presente", 4): ("des",),
        ("subxuntivo.preterito", 0): ("se",), ("subxuntivo.preterito", 3): ("semos",),
        ("indicativo.antepreterito", 0): ("ra",), ("indicativo.antepreterito", 4): ("rades",),
    }
    for (clave, p), terminacions in fins.items():
        for f in t[clave][p]:
            if not f.endswith(terminacions):
                yield f"{clave}.P{p + 1}", t[clave][p], [f"-{x}" for x in terminacions]
    # presente de subxuntivo a partir do presente P1 (falo -> fale, busco -> busque, fago -> faga)
    vogal = "e" if lema.endswith(("ar", "ár")) else "a"
    for p1 in t["indicativo.presente"][0]:
        if not p1.endswith("o"):
            continue
        raiz = p1[:-1]
        if vogal == "e":
            for vello, novo in (("gu", "gü"), ("c", "qu"), ("g", "gu"), ("z", "c")):
                if raiz.endswith(vello):
                    raiz = raiz[: -len(vello)] + novo
                    break
        esperada = raiz + vogal
        if t["subxuntivo.presente"][0] and esperada not in t["subxuntivo.presente"][0] and lema not in IRREGULARES_SUBXUNTIVO:
            yield "subxuntivo.presente.P1 (desde presente P1)", t["subxuntivo.presente"][0], [esperada]
        # pretérito P1 dos verbos en -ar: fale -> falei, busque -> busquei
        if vogal == "e" and t["indicativo.preterito"][0] and sen_til_agudo(esperada) + "i" not in t["indicativo.preterito"][0]:
            yield "indicativo.preterito.P1 (desde subxuntivo)", t["indicativo.preterito"][0], [esperada + "i"]
    # presente P6 = P3 + n (fala -> falan); excepcións: ser, ter, vir e compostos
    p3, p6 = t["indicativo.presente"][2], t["indicativo.presente"][5]
    if p3 and p6 and not any(sen_til_agudo(f) + "n" in [sen_til_agudo(x) for x in p6] for f in p3):
        yield "indicativo.presente.P6 (desde P3)", p6, [f + "n" for f in p3]
    # subxuntivo presente: P2 = P1 + s, P6 = P1 + n
    sp = t["subxuntivo.presente"]
    for p, fin in ((1, "s"), (5, "n")):
        if sp[0] and sp[p] and not all(f + fin in sp[p] for f in sp[0]):
            yield f"subxuntivo.presente.P{p + 1} (desde P1)", sp[p], [f + fin for f in sp[0]]
    for f in t["participio"][:1]:
        if not f.endswith(("ado", "ido", "ído", "to", "so", "cho")):
            yield "participio", t["participio"], ["-ado/-ido"]
    # todas as celas: só letras
    for clave, v in t.items():
        celas = v if isinstance(v[0] if v else [], list) else [v]
        for cela in celas:
            for f in cela:
                if not f.isalpha() or f != f.lower():
                    yield clave, cela, ["só letras minúsculas"]


def revisadas() -> set[tuple[str, str]]:
    ruta = RAIZ / "datos" / "correccions" / "anomalias_revisadas.tsv"
    saida = set()
    for liña in ruta.open(encoding="utf-8"):
        if liña.strip() and not liña.startswith("#"):
            lema, clave = liña.rstrip("\n").split("\t")
            saida.add((lema, clave))
    return saida


def buscar(todas: bool = False) -> dict[str, list]:
    """Anomalías novas (ou todas, con todas=True) agrupadas por comprobación."""
    xa_revisadas = set() if todas else revisadas()
    contas = defaultdict(list)
    ficheiros = [RAIZ / "datos" / "conxugacions.jsonl"] + sorted((RAIZ / "datos" / "capas").glob("*.jsonl"))
    for ficheiro in ficheiros:
        for liña in ficheiro.open(encoding="utf-8"):
            v = json.loads(liña)
            if "taboa" not in v:
                continue
            for clave, obtido, esperado in comprobacions(v["lema"], v["taboa"]):
                if (v["lema"], clave) not in xa_revisadas:
                    contas[clave].append((v["lema"], obtido, esperado))
    return contas


def main():
    """python3 ferramentas/anomalias.py [N] [--todas]: mostra as anomalías novas
    (ou todas). Remata con erro se hai algunha nova."""
    todas = "--todas" in sys.argv
    numeros = [a for a in sys.argv[1:] if a.isdigit()]
    contas = buscar(todas)
    total = 0
    for clave, lista in sorted(contas.items(), key=lambda x: -len(x[1])):
        total += len(lista)
        print(f"\n## {clave}: {len(lista)}")
        for lema, obtido, esperado in lista[: int(numeros[0]) if numeros else 25]:
            print(f"  {lema}: {obtido} (esperado {esperado})")
    print(f"\n{total} anomalías{'' if todas else ' novas'}")
    sys.exit(1 if total and not todas else 0)


if __name__ == "__main__":
    main()
