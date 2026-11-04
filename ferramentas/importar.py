"""Importa as fontes externas ao catálogo de datos/.

Uso:
    python3 ferramentas/descargar.py
    python3 ferramentas/importar.py [--lemas N]

O vocabulario vén só de fontes da Real Academia Galega, a través dos módulos
de Hunspell-gl: o Dicionario da RAG (drag) e o VOLGa (volga). Se un lema está
nos dous, úsase a versión do DRAG, que é a máis recente.

Xera:
    datos/lemas.jsonl         un lema por liña (categoría, xénero, flexión, estado, frecuencia)
    datos/conxugacions.jsonl  táboa de conxugación de cada verbo
    datos/frecuencias.tsv     frecuencia de cada forma no corpus
    datos/nomes.jsonl         nomes propios de persoa (Guía de nomes galegos da RAG)
    datos/locucions.jsonl     locucións da RAG (a pesar de, ao redor, a miúdo...)
    datos/encliticos.jsonl    formas verbais con pronomes enclíticos de uso real
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import conxugacion as C  # noqa: E402
import encliticos  # noqa: E402
from hunspell import Hunspell  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "fontes" / "cache"
HUNSPELL = CACHE / "hunspell-gl"
DATOS = RAIZ / "datos"

# Categoría de Hunspell (po:) -> (categoría propia, xénero, número fixo)
CATEGORIAS = {
    "substantivo_masculino": ("substantivo", "masculino", None),
    "substantivo_feminino": ("substantivo", "feminino", None),
    "substantivo": ("substantivo", None, None),
    "substantivo_masculino_plural": ("substantivo", "masculino", "plural"),
    "substantivo_feminino_plural": ("substantivo", "feminino", "plural"),
    "substantivo_plural": ("substantivo", None, "plural"),
    "adxectivo": ("adxectivo", None, None),
    "adxectivos": ("adxectivo", None, None),
    "adxectivo_masculino": ("adxectivo", "masculino", None),
    "adxectivo_feminino": ("adxectivo", "feminino", None),
    "adxectivo_plural": ("adxectivo", None, "plural"),
    "verbo": ("verbo", None, None),
    "verbo_intransitiva": ("verbo", None, None),
    "adverbio": ("adverbio", None, None),
    "adverbio_latino": ("adverbio", None, None),
    "artigo_determinado": ("artigo", None, None),
    "artigo_indeterminado": ("artigo", None, None),
    "pronome_persoal": ("pronome_persoal", None, None),
    "pronome": ("pronome", None, None),
    "demostrativo": ("demostrativo", None, None),
    "posesivo": ("posesivo", None, None),
    "posesivo_masculino": ("posesivo", "masculino", None),
    "posesivo_feminino": ("posesivo", "feminino", None),
    "indefinido": ("indefinido", None, None),
    "relativo": ("relativo", None, None),
    "interrogativo": ("interrogativo", None, None),
    "exclamativo": ("exclamativo", None, None),
    "numeral": ("numeral", None, None),
    "numeral_masculino": ("numeral", "masculino", None),
    "numeral_feminino": ("numeral", "feminino", None),
    "numeral_ordinal": ("numeral", None, None),
    "preposición": ("preposición", None, None),
    "conxunción": ("conxunción", None, None),
    "interxección": ("interxección", None, None),
    "exclamación": ("interxección", None, None),
    "contracción": ("contracción", None, None),
}
# Non se importan: siglas, abreviaturas, símbolos, participios (van co verbo),
# locucións e nomes propios. Algúns poden engadirse máis adiante.

PALABRAS_GRAMATICAIS = {
    "artigo", "pronome_persoal", "pronome", "demostrativo", "posesivo", "indefinido", "relativo",
    "interrogativo", "exclamativo", "preposición", "conxunción", "contracción", "adverbio",
    "numeral", "interxección",
}


def modulos() -> list[tuple[str, str, Path]]:
    """[(fonte, estado, ruta)] na orde de preferencia (DRAG primeiro)."""
    fontes = json.loads((RAIZ / "fontes" / "fontes.json").read_text(encoding="utf-8"))
    saida = []
    for fonte in ("drag", "volga"):
        for ruta, estado in fontes[fonte]["modulos"].items():
            saida.append((fonte, estado, HUNSPELL / "src" / ruta))
    return saida


def clave_orde(texto: str) -> tuple:
    return (C.sen_acentos(texto).replace("ñ", "n~"), texto)


def xenero_numero(morph: tuple[str, ...], xenero_base: str | None, numero_base: str | None) -> str:
    """Clave de flexión nominal: ms, mp, fs, fp."""
    texto = " ".join(morph)
    xenero = "f" if ("feminino" in texto or xenero_base == "feminino") else "m"
    numero = "p" if ("plural" in texto or numero_base == "plural") else "s"
    return xenero + numero


def palabra_valida(palabra: str) -> bool:
    """Palabras comúns: minúsculas, letras e como moito guións interiores."""
    return palabra.islower() and palabra.replace("-", "").isalpha() and not palabra.startswith("-")


CATEGORIAS_PECHADAS = {"artigo", "pronome_persoal", "pronome", "demostrativo", "posesivo", "indefinido",
                       "relativo", "interrogativo", "exclamativo", "contracción"}


def axustar_gramaticais(rexistros: dict) -> None:
    """Limpa as palabras gramaticais segundo datos/correccions/gramaticais.json
    e quita lemas que son formas doutro lema da mesma categoría (da -> do)."""
    axustes = json.loads((DATOS / "correccions" / "gramaticais.json").read_text(encoding="utf-8"))
    for orixe, destino in axustes["unir"]:
        if orixe in rexistros and destino in rexistros:
            r, d = rexistros.pop(orixe), rexistros[destino]
            for clave, lista in r["formas"].items():
                d["formas"][clave] += [f for f in lista if f not in d["formas"][clave]]
            d["frecuencia"] += r["frecuencia"]
            d["fontes"] = list(dict.fromkeys(d["fontes"] + r["fontes"]))
    for ident, categoria in axustes["categoria"].items():
        if ident in rexistros:
            r = rexistros.pop(ident)
            novo = f"{r['lema']}#{categoria}"
            r["id"], r["categoria"] = novo, categoria
            if novo in rexistros:   # xa existía: xuntar
                rexistros[novo]["frecuencia"] += r["frecuencia"]
            else:
                rexistros[novo] = r
    # lemas que son forma (non base) doutro lema da mesma categoría pechada.
    # Os pronomes persoais non: «nos» (P4) non é o plural de «no» (= o).
    formas_de: dict[tuple[str, str], str] = {}
    for ident, r in rexistros.items():
        if r["categoria"] in CATEGORIAS_PECHADAS - {"pronome_persoal"}:
            for lista in r["formas"].values():
                for forma in lista:
                    if forma != r["lema"]:
                        formas_de.setdefault((forma, r["categoria"]), ident)
    for ident in list(rexistros):
        r = rexistros[ident]
        destino = formas_de.get((r["lema"], r["categoria"]))
        if destino and destino != ident and destino in rexistros:
            d = rexistros[destino]
            xa = {f for lista in d["formas"].values() for f in lista}
            for clave, lista in r["formas"].items():
                d["formas"][clave] += [f for f in lista if f not in xa]
            d["frecuencia"] += r["frecuencia"]
            del rexistros[ident]
    for ident, r in rexistros.items():
        if r["categoria"] == "contracción":
            r["composicion"] = axustes["composicion"].get(r["lema"])


def escribir_nomes() -> int:
    """datos/nomes.jsonl: nomes de persoa da Guía de nomes galegos da RAG."""
    fontes = json.loads((RAIZ / "fontes" / "fontes.json").read_text(encoding="utf-8"))
    nomes = {}
    for ruta in fontes["rag-nomes"]["modulos"]:
        for liña in (HUNSPELL / "src" / ruta).open(encoding="utf-8"):
            liña = liña.split("#", 1)[0].strip()
            if not liña:
                continue
            nome, *morph = liña.split()
            nome = nome.split("/")[0]
            tipo = next((m[3:] for m in morph if m.startswith("po:")), None)
            nomes.setdefault(nome, {"nome": nome, "tipo": tipo, "fontes": ["rag-nomes"]})
    with (DATOS / "nomes.jsonl").open("w", encoding="utf-8") as fh:
        for nome in sorted(nomes, key=clave_orde):
            fh.write(json.dumps(nomes[nome], ensure_ascii=False) + "\n")
    return len(nomes)


LOCUCION_POR_CATEGORIA = {"adverbio": "locución adverbial", "preposición": "locución preposicional",
                          "conxunción": "locución conxuntiva", "adxectivo": "locución adxectiva",
                          "pronome": "locución pronominal", "interxección": "locución interxectiva"}
FUNCIONAIS = {"a", "á", "ao", "ó", "ás", "ós", "aos", "de", "do", "da", "dos", "das", "en", "no", "na",
              "nos", "nas", "por", "polo", "pola", "con", "co", "coa", "sen", "ata", "tras", "o", "os", "as",
              "un", "unha", "dun", "dunha", "nun", "nunha"}


def escribir_locucions(h, fonte_de) -> int:
    """datos/locucions.jsonl: locucións da RAG, reconstruídas das etiquetas
    is:ngrama_ (cada palabra da locución é unha entrada co n-grama completo)."""
    locucions: dict[str, dict] = {}
    for e in h.entries:
        if e.source not in fonte_de:
            continue
        ngrama = next((m[len("is:ngrama_"):] for m in e.morph if m.startswith("is:ngrama_")), None)
        if not ngrama or ngrama[0].isupper():
            continue
        fonte, _ = fonte_de[e.source]
        frase = ngrama.replace("_", " ")
        palabras = frase.split()
        # o VOLGa garda algunhas coa palabra clave diante («pesar de a»)
        while len(palabras) > 1 and palabras[-1] in FUNCIONAIS and palabras[0] not in FUNCIONAIS:
            palabras.insert(0, palabras.pop())
        frase = " ".join(palabras)
        categorias = set()
        for po in e.fields("po"):
            if po.startswith("locución"):
                categorias.add(po.replace("_", " "))
            elif po.startswith("substantivo"):
                categorias.add("locución substantiva")
            elif po in LOCUCION_POR_CATEGORIA:
                categorias.add(LOCUCION_POR_CATEGORIA[po])
        r = locucions.setdefault(frase, {"locucion": frase, "categorias": set(), "fontes": []})
        r["categorias"] |= categorias
        if fonte not in r["fontes"]:
            r["fontes"].append(fonte)
    with (DATOS / "locucions.jsonl").open("w", encoding="utf-8") as fh:
        for frase in sorted(locucions, key=clave_orde):
            r = locucions[frase]
            r["categorias"] = sorted(r["categorias"]) or ["locución"]
            r["fontes"] = [f for f in ("drag", "volga") if f in r["fontes"]]
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(locucions)


def ler_frecuencias(ruta: Path) -> dict[str, int]:
    frec: dict[str, int] = defaultdict(int)
    with ruta.open(encoding="utf-8") as fh:
        for liña in fh:
            partes = liña.split()
            if len(partes) == 2 and partes[1].isdigit():
                frec[partes[0].lower()] += int(partes[1])
    return frec


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--lemas", type=int, default=0,
                      help="importar só os N lemas máis frecuentes (por defecto, todos)")
    opcions = args.parse_args()

    mods = modulos()
    fonte_de = {str(ruta): (fonte, estado) for fonte, estado, ruta in mods}
    h = Hunspell(HUNSPELL / "gl.aff", [ruta for _, _, ruta in mods])
    frecuencias = ler_frecuencias(CACHE / "frecuencias-opensubtitles" / "gl_full.txt")
    correccions = json.loads((DATOS / "correccions" / "conxugacions.json").read_text(encoding="utf-8"))

    def utilizable(e) -> bool:
        return (e.source in fonte_de and palabra_valida(e.word)
                and not any(m.startswith("is:ngrama_") for m in e.morph))   # anacos de locucións

    # 1. Que fontes ten cada lema: (lema, categoría) -> {fonte: estado} ------
    presenza: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for e in h.entries:
        if not utilizable(e):
            continue
        fonte, estado = fonte_de[e.source]
        for po in e.fields("po"):
            if po in CATEGORIAS:
                estados = presenza[(e.word, CATEGORIAS[po][0])]
                # se unha fonte o ten como recomendado e tolerado, queda recomendado
                if estados.get(fonte) != "recomendado":
                    estados[fonte] = estado

    # O VOLGa só achega lemas que non están no DRAG (p. ex. «curuxa»). Se o
    # DRAG ten o lema, as súas categorías mandan: o VOLGa usa etiquetas máis
    # xerais («pronome») e lista formas como lemas («ela», «túa»).
    lemas_drag = {lema for (lema, _), estados in presenza.items() if "drag" in estados}
    for (lema, categoria) in list(presenza):
        if lema in lemas_drag and "drag" not in presenza[(lema, categoria)]:
            del presenza[(lema, categoria)]
        elif lema not in lemas_drag and categoria == "pronome":
            del presenza[(lema, categoria)]

    def fonte_principal(lema: str, categoria: str) -> str | None:
        estados = presenza.get((lema, categoria))
        if not estados:
            return None
        return "drag" if "drag" in estados else "volga"

    # 2. Lemas e formas, só desde a fonte principal de cada lema ---------------
    rexistros: dict[str, dict] = {}
    omitir = C.omitir_encliticos(h)
    for e in h.entries:
        if not utilizable(e) or h.needaffix in e.flags:
            continue
        fonte, _ = fonte_de[e.source]
        for po in e.fields("po"):
            if po not in CATEGORIAS:
                continue
            categoria, xenero, numero = CATEGORIAS[po]
            if fonte != fonte_principal(e.word, categoria):
                continue
            ident = f"{e.word}#{categoria}"
            r = rexistros.setdefault(ident, {
                "id": ident, "lema": e.word, "categoria": categoria,
                "xeneros": set(), "formas": defaultdict(list), "tipos": [],
            })
            if xenero:
                r["xeneros"].add(xenero)
            if categoria == "verbo":
                for t in e.fields("ts"):
                    for tipo in t.split("_"):
                        if tipo not in r["tipos"]:
                            r["tipos"].append(tipo)
                continue
            for f in h.expand(e, omitir):
                clave = xenero_numero(f.morph, xenero, numero)
                if f.form not in r["formas"][clave]:
                    r["formas"][clave].append(f.form)

    for r in rexistros.values():
        estados = presenza[(r["lema"], r["categoria"])]
        r["fontes"] = [f for f in ("drag", "volga") if f in estados]
        r["estado"] = estados[r["fontes"][0]]

    verbos = {r["lema"]: fonte_principal(r["lema"], "verbo")
              for r in rexistros.values() if r["categoria"] == "verbo"}
    def admitir_verbo(entrada, lema) -> bool:
        return fonte_de.get(entrada.source, ("",))[0] == verbos[lema]

    taboas = C.taboas_desde_hunspell(h, set(verbos), admitir=admitir_verbo)
    for lema, taboa in taboas.items():
        C.completar(taboa, lema)

    # 3. Frecuencia de cada lema: suma das súas formas -------------------------
    #    Unha forma ambigua repártese en proporción á "evidencia" de cada lema:
    #    a frecuencia das súas formas non ambiguas e da súa forma de cita,
    #    cun peso moito maior para as palabras gramaticais ("para" preposición
    #    fronte a "parar").
    forma_lemas: dict[str, set[str]] = defaultdict(set)
    for ident, r in rexistros.items():
        if r["categoria"] == "verbo":
            for forma, _, _ in C.formas(taboas[r["lema"]]):
                forma_lemas[forma].add(ident)
        else:
            forma_lemas[r["lema"]].add(ident)
            for lista in r["formas"].values():
                for forma in lista:
                    forma_lemas[forma].add(ident)
    evidencia = {ident: 1.0 for ident in rexistros}
    for forma, idents in forma_lemas.items():
        if len(idents) == 1:
            evidencia[next(iter(idents))] += frecuencias.get(forma, 0)
    for ident, r in rexistros.items():
        evidencia[ident] += frecuencias.get(r["lema"], 0)
        if r["categoria"] in PALABRAS_GRAMATICAIS:
            evidencia[ident] *= 100_000
        r["frecuencia"] = 0.0
    for forma, idents in forma_lemas.items():
        n = frecuencias.get(forma, 0)
        if not n:
            continue
        total = sum(evidencia[i] for i in idents)
        for ident in idents:
            rexistros[ident]["frecuencia"] += n * evidencia[ident] / total

    axustar_gramaticais(rexistros)
    escollidos = sorted(rexistros.values(), key=lambda r: -r["frecuencia"])
    if opcions.lemas:
        escollidos = escollidos[: opcions.lemas]
    escollidos.sort(key=lambda r: (clave_orde(r["lema"]), r["categoria"]))

    # 4. Correccións manuais e revisión das táboas -----------------------------
    saidas_verbos = []
    sen_completar = []
    for r in escollidos:
        if r["categoria"] != "verbo":
            continue
        lema = r["lema"]
        taboa = taboas[lema]
        saida = {"lema": lema, "fontes": ["hunspell-gl"]}
        correccion = correccions.get(lema) or C.correccion_derivada(lema, correccions)
        if correccion:
            saida["correccions"] = C.aplicar_correccion(taboa, correccion)
            saida["fontes"] = ["hunspell-gl", "revision-manual"]
        if C.unipersoal(taboa) and "unipersoal" not in r["tipos"]:
            r["tipos"].append("unipersoal")
        if C.defectivo(taboa) and "defectivo" not in r["tipos"]:
            r["tipos"].append("defectivo")
        faltan = C.baleiras(taboa)
        if faltan and not {"defectivo", "unipersoal", "impersoal"} & set(r["tipos"]) and lema != "haber":
            saida["baleiras"] = faltan
            sen_completar.append(lema)
        saida["taboa"] = taboa
        saidas_verbos.append(saida)

    # 5. Escribir datos/ --------------------------------------------------
    formas_catalogo: set[str] = set()
    with (DATOS / "lemas.jsonl").open("w", encoding="utf-8") as fh:
        for r in escollidos:
            saida = {"id": r["id"], "lema": r["lema"], "categoria": r["categoria"]}
            if r["xeneros"]:
                saida["xenero"] = "/".join(sorted(r["xeneros"]))
            if r["tipos"]:
                saida["tipos"] = r["tipos"]
            if r["categoria"] != "verbo":
                saida["formas"] = {k: r["formas"][k] for k in ("ms", "fs", "mp", "fp") if r["formas"].get(k)}
                formas_catalogo.update(f for lista in saida["formas"].values() for f in lista)
            formas_catalogo.add(r["lema"])
            if r.get("composicion"):
                saida["composicion"] = r["composicion"]
            saida["estado"] = r["estado"]
            saida["frecuencia"] = round(r["frecuencia"])
            saida["fontes"] = r["fontes"]
            fh.write(json.dumps(saida, ensure_ascii=False) + "\n")

    with (DATOS / "conxugacions.jsonl").open("w", encoding="utf-8") as fh:
        for saida in saidas_verbos:
            formas_catalogo.update(f for f, _, _ in C.formas(saida["taboa"]))
            fh.write(json.dumps(saida, ensure_ascii=False) + "\n")

    with (DATOS / "frecuencias.tsv").open("w", encoding="utf-8") as fh:
        fh.write("# forma\tfrecuencia  (fonte: FrequencyWords/OpenSubtitles 2018, CC BY-SA 4.0)\n")
        for forma in sorted(formas_catalogo, key=clave_orde):
            if frecuencias.get(forma):
                fh.write(f"{forma}\t{frecuencias[forma]}\n")

    n_nomes = escribir_nomes()
    n_loc = escribir_locucions(h, fonte_de)

    encl = encliticos.buscar(h, set(verbos), admitir_verbo, frecuencias, formas_catalogo,
                             {v["lema"]: v["taboa"] for v in saidas_verbos})
    with (DATOS / "encliticos.jsonl").open("w", encoding="utf-8") as fh:
        for r in encl:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    if encliticos.CORRECCIONS_TIL:
        print(f"{len(set(encliticos.CORRECCIONS_TIL))} formas do corpus con til corrixido: "
              + ", ".join(f"{a}→{b}" for a, b, _, _ in sorted(set(encliticos.CORRECCIONS_TIL))[:12]))

    n_verbos = sum(1 for r in escollidos if r["categoria"] == "verbo")
    print(f"{len(escollidos)} lemas ({n_verbos} verbos), {len(formas_catalogo)} formas, "
          f"{len(encl)} formas con enclíticos, {n_nomes} nomes propios, {n_loc} locucións.")
    if sen_completar:
        print(f"{len(sen_completar)} verbos con celas baleiras: {', '.join(sen_completar[:40])}")


if __name__ == "__main__":
    main()
