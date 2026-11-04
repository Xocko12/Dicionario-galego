"""Comproba que datos/ está ben formado.

    python3 ferramentas/validar.py            # estrutura (sen dependencias)
    python3 ferramentas/validar.py --hunspell # e ademais, que Hunspell acepta cada forma

A segunda comprobación usa spylls (implementación de Hunspell en Python,
independente do noso lector) e precisa as fontes descargadas.
Remata con erro se atopa problemas de estrutura. As formas que Hunspell
non recoñece só se informan, porque poden ser correccións correctas.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conxugacion as C  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"

CATEGORIAS = {"substantivo", "adxectivo", "verbo", "adverbio", "artigo", "pronome_persoal", "pronome",
              "demostrativo", "posesivo", "indefinido", "relativo", "interrogativo", "exclamativo",
              "numeral", "preposición", "conxunción", "interxección", "contracción"}
ESTADOS = {"recomendado", "tolerado"}
CLAVES_FORMAS = {"ms", "mp", "fs", "fp"}


def ler_jsonl(ruta: Path):
    with ruta.open(encoding="utf-8") as fh:
        for n, liña in enumerate(fh, 1):
            yield n, json.loads(liña)


def validar_estrutura() -> tuple[list[str], set[str]]:
    erros: list[str] = []
    formas: set[str] = set()
    fontes = set(json.loads((RAIZ / "fontes" / "fontes.json").read_text(encoding="utf-8")))
    ids = set()
    verbos = set()
    for n, r in ler_jsonl(DATOS / "lemas.jsonl"):
        onde = f"lemas.jsonl:{n}"
        for campo in ("id", "lema", "categoria", "frecuencia", "fontes"):
            if campo not in r:
                erros.append(f"{onde}: falta '{campo}'")
        if r.get("id") in ids:
            erros.append(f"{onde}: id repetido {r.get('id')}")
        ids.add(r.get("id"))
        if r.get("id") != f"{r.get('lema')}#{r.get('categoria')}":
            erros.append(f"{onde}: o id debe ser lema#categoria")
        if r.get("categoria") not in CATEGORIAS:
            erros.append(f"{onde}: categoría descoñecida {r.get('categoria')}")
        if r.get("estado") not in ESTADOS:
            erros.append(f"{onde}: estado descoñecido {r.get('estado')}")
        if r.get("categoria") == "contracción" and not r.get("composicion"):
            erros.append(f"{onde}: contracción sen composición")
        for f in r.get("fontes", []):
            if f not in fontes:
                erros.append(f"{onde}: fonte sen describir en fontes.json: {f}")
        if r.get("categoria") == "verbo":
            verbos.add(r["lema"])
        else:
            for clave, lista in r.get("formas", {}).items():
                if clave not in CLAVES_FORMAS:
                    erros.append(f"{onde}: clave de forma descoñecida {clave}")
                formas.update(lista)
        formas.add(r.get("lema", ""))

    con_taboa = set()
    for n, v in ler_jsonl(DATOS / "conxugacions.jsonl"):
        onde = f"conxugacions.jsonl:{n}"
        lema = v.get("lema")
        con_taboa.add(lema)
        if lema not in verbos:
            erros.append(f"{onde}: {lema} non está en lemas.jsonl como verbo")
        taboa = v.get("taboa", {})
        for clave, _ in C.TEMPOS:
            celas = taboa.get(clave)
            if not isinstance(celas, list) or len(celas) != 6:
                erros.append(f"{onde}: {lema}: '{clave}' debe ter 6 celas")
        for forma, _, _ in C.formas(taboa):
            if not forma or forma != forma.strip() or " " in forma:
                erros.append(f"{onde}: {lema}: forma incorrecta {forma!r}")
            formas.add(forma)
    pronomes_validos = {"me", "te", "che", "lle", "lles", "nos", "vos", "se", "o", "a", "os", "as"}
    for n, r in ler_jsonl(DATOS / "encliticos.jsonl"):
        onde = f"encliticos.jsonl:{n}"
        if r.get("lema") not in verbos:
            erros.append(f"{onde}: {r.get('lema')} non é un verbo do catálogo")
        if not r.get("pronomes") or not set(r["pronomes"]) <= pronomes_validos or len(r["pronomes"]) > 2:
            erros.append(f"{onde}: pronomes incorrectos {r.get('pronomes')}")
        if not r.get("base"):
            erros.append(f"{onde}: falta a forma base")
        formas.add(r.get("forma", ""))
    for n, r in ler_jsonl(DATOS / "nomes.jsonl"):
        if not r.get("nome") or not r["nome"][0].isupper() or r.get("tipo") != "antropónimo":
            erros.append(f"nomes.jsonl:{n}: nome incorrecto {r}")
    dous_tiles = re.compile(r"[áéíóú].*[áéíóú]")
    for forma in formas:
        if dous_tiles.search(forma) and "-" not in forma:
            erros.append(f"forma con dous tiles: {forma}")
    for lema in sorted(verbos - con_taboa):
        erros.append(f"lemas.jsonl: o verbo {lema} non ten táboa en conxugacions.jsonl")
    return erros, formas


def formas_corrixidas() -> set[str]:
    """Formas que veñen de correccións manuais (poden faltar en Hunspell
    precisamente porque alí están mal)."""
    saida = set()
    for _, v in ler_jsonl(DATOS / "conxugacions.jsonl"):
        for clave in v.get("correccions", []):
            base, _, persoa = clave.rpartition(".")
            if persoa in C.PERSOAS:
                saida.update(v["taboa"][base][C.PERSOAS.index(persoa)])
            elif isinstance(v["taboa"][clave][0] if v["taboa"][clave] else "", list):
                saida.update(f for cela in v["taboa"][clave] for f in cela)
            else:
                saida.update(v["taboa"][clave])
    return saida


def validar_hunspell(formas: set[str]) -> list[str]:
    from spylls.hunspell import Dictionary
    cache = RAIZ / "fontes" / "cache" / "hunspell-gl" / "gl"
    dic = Dictionary.from_files(str(cache))
    return sorted(f for f in formas if not dic.lookup(f))


def main() -> None:
    erros, formas = validar_estrutura()
    for e in erros[:200]:
        print("ERRO", e)
    print(f"{len(formas)} formas; {len(erros)} erros de estrutura.")
    if "--hunspell" in sys.argv:
        descoñecidas = validar_hunspell(formas)
        corrixidas = formas_corrixidas()
        esperadas = [f for f in descoñecidas if f in corrixidas]
        novas = [f for f in descoñecidas if f not in corrixidas]
        print(f"{len(esperadas)} formas corrixidas a man que Hunspell non ten (esperado):")
        print("  " + ", ".join(esperadas[:300]))
        print(f"{len(novas)} formas que Hunspell non recoñece:")
        print("  " + ", ".join(novas[:300]))
        if novas:
            erros.append("formas sen recoñecer")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
