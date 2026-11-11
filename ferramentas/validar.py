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
        # os diminutivos non van a «formas»: Hunspell-gl non ten regras de diminutivo
        if "diminutivos" in r and r.get("categoria") not in ("substantivo", "adxectivo"):
            erros.append(f"{onde}: só os substantivos e os adxectivos levan diminutivos")
        for clave, lista in r.get("diminutivos", {}).items():
            if clave not in CLAVES_FORMAS:
                erros.append(f"{onde}: clave de diminutivo descoñecida {clave}")
            for f in lista:
                if not re.fullmatch(r"[a-zñáéíóúü]+[ií]ñ[oa]" + ("s" if clave.endswith("p") else ""), f):
                    erros.append(f"{onde}: diminutivo incorrecto {f!r} ({clave})")
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
    for n, r in ler_jsonl(DATOS / "locucions.jsonl"):
        if not r.get("locucion") or " " not in r["locucion"] or not r.get("categorias"):
            erros.append(f"locucions.jsonl:{n}: locución incorrecta {r}")
    for n, r in ler_jsonl(DATOS / "sinonimos.jsonl"):
        if not r.get("lema") or not r.get("sinonimos") or any(not x.get("forma") for x in r["sinonimos"]):
            erros.append(f"sinonimos.jsonl:{n}: entrada incorrecta {r}")
    erros += validar_capas(formas)

    dous_tiles = re.compile(r"[áéíóú].*[áéíóú]")
    for forma in formas:
        if dous_tiles.search(forma) and "-" not in forma:
            erros.append(f"forma con dous tiles: {forma}")
    for lema in sorted(verbos - con_taboa):
        erros.append(f"lemas.jsonl: o verbo {lema} non ten táboa en conxugacions.jsonl")
    return erros, formas


def validar_capas(formas: set[str]) -> list[str]:
    """Estrutura de datos/capas/*.jsonl segundo o tipo de cada capa."""
    erros = []
    config = json.loads((RAIZ / "fontes" / "capas.json").read_text(encoding="utf-8"))["capas"]
    ids_core = {r["id"] for _, r in ler_jsonl(DATOS / "lemas.jsonl")}
    vistos = set()
    for capa, cfg in config.items():
        ruta = DATOS / "capas" / f"{capa}.jsonl"
        if not ruta.exists():
            if not cfg.get("opcional"):
                erros.append(f"falta datos/capas/{capa}.jsonl")
            continue
        for n, r in ler_jsonl(ruta):
            onde = f"capas/{capa}.jsonl:{n}"
            if r.get("capa") != capa:
                erros.append(f"{onde}: campo capa incorrecto")
            if cfg["tipo"] == "lexico":
                if r.get("id") in ids_core or r.get("id") in vistos:
                    erros.append(f"{onde}: {r.get('id')} repetido (núcleo ou capa anterior)")
                vistos.add(r.get("id"))
                if r.get("categoria") not in CATEGORIAS or not r.get("fontes"):
                    erros.append(f"{onde}: categoría ou fontes incorrectas")
                if r.get("categoria") == "verbo":
                    taboa = r.get("taboa", {})
                    for clave, _ in C.TEMPOS:
                        if len(taboa.get(clave, [])) != 6:
                            erros.append(f"{onde}: {r.get('lema')}: '{clave}' debe ter 6 celas")
                    formas.update(f for f, _, _ in C.formas(taboa))
                else:
                    formas.update(f for lista in r.get("formas", {}).values() for f in lista)
            elif cfg["tipo"] == "siglas":
                if not r.get("forma") or not r.get("tipo"):
                    erros.append(f"{onde}: sigla sen forma ou tipo")
            elif cfg["tipo"] == "onomastica":
                if not r.get("nome") or not r.get("tipo") or r["nome"] != r["nome"].strip():
                    erros.append(f"{onde}: nome incorrecto {r}")
            elif cfg["tipo"] == "codigos":
                if not r.get("codigo"):
                    erros.append(f"{onde}: código baleiro")
            elif cfg["tipo"] == "semantica":
                if not r.get("lema") or not r.get("sentidos") or any("ili" not in x for x in r["sentidos"]):
                    erros.append(f"{onde}: sentido incorrecto")
            elif cfg["tipo"] == "traducions":
                if not r.get("lema") or not any(r.get(l) for l in ("es", "pt", "en")):
                    erros.append(f"{onde}: sen traducións")
            elif cfg["tipo"] == "definicions":
                if not r.get("lema") or not r.get("acepcions") or any(not a.get("definicion") for a in r["acepcions"]):
                    erros.append(f"{onde}: definición incorrecta")
    return erros


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
