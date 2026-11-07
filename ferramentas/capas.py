"""Importa as capas opcionais (fontes/capas.json) a datos/capas/<capa>.jsonl.

    python3 ferramentas/capas.py [capa ...]

Capas léxicas (digalego, comunidade, terminoloxía): mesmo formato ca
datos/lemas.jsonl, máis o campo "capa"; os verbos levan a táboa de
conxugación dentro ("taboa"). Un lema que xa está no núcleo da RAG, ou nunha
capa anterior, non se repite.

Siglas:      {"forma": "NIF", "tipo": "sigla", "nota": "Número de identificación fiscal", ...}
Onomástica:  {"nome": "Santiago de Compostela", "tipo": "topónimo", ...}
Códigos:     {"codigo": "glg", "tipo": "iso639", "nota": "Galician (639-2/3)"}
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compostos  # noqa: E402
import conxugacion as C  # noqa: E402
import importar as I  # noqa: E402
from hunspell import Hunspell  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SRC = I.HUNSPELL / "src"
SAIDA = I.DATOS / "capas"

# cartafol de Hunspell-gl -> nome de fonte
FONTES = {"xunta": "digalego", "rag/gl": "drag", "rag/volga": "volga", "rag": "drag",
          "wikipedia/gl": "wikipedia-gl", "wikipedia/en": "wikipedia-en", "wikipedia/es": "wikipedia-es",
          "wikipedia/pt": "wikipedia-pt", "wikipedia/hu": "wikipedia-hu",
          "wiktionary/gl": "wiktionary-gl", "wiktionary/en": "wiktionary-en"}

FUNCIONAIS = {"a", "á", "ao", "ó", "ás", "ós", "aos", "de", "do", "da", "dos", "das", "en", "no", "na",
              "nos", "nas", "por", "polo", "pola", "con", "co", "coa", "sen", "ata", "tras", "o", "os", "as",
              "un", "unha", "dun", "dunha", "nun", "nunha"}


def ficheiros(patron: str) -> list[Path]:
    if "*" in patron:
        return sorted(SRC.glob(patron))
    ruta = SRC / patron
    if ruta.is_dir():
        return sorted(ruta.rglob("*.dic"))
    return [ruta] if ruta.exists() else []


def fonte_de(ruta: Path) -> str:
    rel = ruta.relative_to(SRC).parts
    for n in (2, 1):
        clave = "/".join(rel[:n])
        if clave in FONTES:
            return FONTES[clave]
    return rel[0]


def liñas(ruta: Path):
    """(palabra, flags, etiquetas, comentario) de cada liña útil dun .dic."""
    for raw in ruta.open(encoding="utf-8", errors="replace"):
        texto, _, comentario = raw.partition("#")
        texto = texto.strip()
        if not texto:
            continue
        cabeza, *etiquetas = texto.split()
        palabra, _, flags = cabeza.partition("/")
        yield palabra, flags, etiquetas, comentario.strip()


def frase_ngrama(etiquetas: list[str]) -> str | None:
    for e in etiquetas:
        if e.startswith("is:ngrama_"):
            return e[len("is:ngrama_"):].replace("_", " ")
    return None


def rotar_locucion(frase: str) -> str:
    """O VOLGa garda algunhas locucións coa palabra clave diante («pesar de a»);
    as palabras funcionais finais volven ao principio: «a pesar de»."""
    palabras = frase.split()
    while len(palabras) > 1 and palabras[-1] in FUNCIONAIS and palabras[0] not in FUNCIONAIS:
        palabras.insert(0, palabras.pop())
    return " ".join(palabras)


# -- capas léxicas ------------------------------------------------------------

def importar_lexico(capa: str, rutas: list[Path], h: Hunspell, frecuencias, correccions, referencia, xa_vistos: set[str]):
    fontes_ruta = {str(r): fonte_de(r) for r in rutas}
    omitir = C.omitir_encliticos(h)
    rexistros: dict[str, dict] = {}
    for e in h.entries:
        if e.source not in fontes_ruta or not I.palabra_valida(e.word) or h.needaffix in e.flags:
            continue
        if any(m.startswith("is:ngrama_") for m in e.morph):
            continue
        for po in e.fields("po"):
            if po not in I.CATEGORIAS:
                continue
            categoria, xenero, numero = I.CATEGORIAS[po]
            ident = f"{e.word}#{categoria}"
            if ident in xa_vistos:
                continue
            r = rexistros.setdefault(ident, {
                "id": ident, "lema": e.word, "categoria": categoria, "capa": capa,
                "xeneros": set(), "formas": defaultdict(list), "tipos": [], "fontes": [],
            })
            fonte = fontes_ruta[e.source]
            if fonte not in r["fontes"]:
                r["fontes"].append(fonte)
            if xenero:
                r["xeneros"].add(xenero)
            if categoria == "verbo":
                for t in e.fields("ts"):
                    for tipo in t.split("_"):
                        if tipo not in r["tipos"]:
                            r["tipos"].append(tipo)
                continue
            for f in h.expand(e, omitir):
                clave = I.xenero_numero(f.morph, xenero, numero)
                if f.form not in r["formas"][clave]:
                    r["formas"][clave].append(f.form)

    verbos = {r["lema"] for r in rexistros.values() if r["categoria"] == "verbo"}
    taboas = C.taboas_desde_hunspell(h, verbos, admitir=lambda e, lema: e.source in fontes_ruta)
    saida = []
    for ident in sorted(rexistros, key=lambda i: (I.clave_orde(rexistros[i]["lema"]), i)):
        r = rexistros[ident]
        s = {"id": r["id"], "lema": r["lema"], "categoria": r["categoria"], "capa": capa}
        if r["xeneros"]:
            s["xenero"] = "/".join(sorted(r["xeneros"]))
        if r["tipos"]:
            s["tipos"] = r["tipos"]
        formas = {r["lema"]}
        if r["categoria"] == "verbo":
            taboa = taboas.get(r["lema"]) or C.taboa_baleira(r["lema"])
            C.completar(taboa, r["lema"])
            correccion = correccions.get(r["lema"]) or C.correccion_derivada(r["lema"], correccions)
            if correccion:
                s["correccions"] = C.aplicar_correccion(taboa, correccion)
            if r["lema"] in referencia:
                cambiadas = C.aplicar_referencia(taboa, referencia[r["lema"]])
                if cambiadas:
                    s["referencia"] = cambiadas
            if C.unipersoal(taboa) and "unipersoal" not in s.setdefault("tipos", []):
                s["tipos"].append("unipersoal")
            if C.defectivo(taboa) and "defectivo" not in s.setdefault("tipos", []):
                s["tipos"].append("defectivo")
            faltan = C.baleiras(taboa)
            if faltan and not {"defectivo", "unipersoal", "impersoal"} & set(s.get("tipos", [])):
                s["baleiras"] = faltan
            s["taboa"] = taboa
            formas.update(f for f, _, _ in C.formas(taboa))
        else:
            s["formas"] = {k: r["formas"][k] for k in ("ms", "fs", "mp", "fp") if r["formas"].get(k)}
            formas.update(f for lista in s["formas"].values() for f in lista)
        s["frecuencia"] = sum(frecuencias.get(f, 0) for f in formas)
        s["fontes"] = r["fontes"]
        saida.append(s)
        xa_vistos.add(ident)
    return saida


# -- siglas, onomástica, códigos ----------------------------------------------

TIPOS_SIGLAS = {"sigla", "abreviatura", "símbolo"}


def importar_siglas(capa: str, rutas: list[Path]):
    """Siglas, abreviaturas e símbolos. Nos módulos mixtos (rag/gl/correcto.dic)
    só entran as entradas con esa categoría."""
    vistos = {}
    for ruta in rutas:
        fonte = fonte_de(ruta)
        for palabra, _, etiquetas, nota in liñas(ruta):
            if frase_ngrama(etiquetas):
                continue
            tipo = next((e[3:] for e in etiquetas if e.startswith("po:")), "sigla")
            if tipo not in TIPOS_SIGLAS:
                continue
            clave = (palabra, tipo)
            r = vistos.setdefault(clave, {"forma": palabra, "tipo": tipo, "capa": capa, "fontes": []})
            if fonte not in r["fontes"]:
                r["fontes"].append(fonte)
            if nota and not r.get("nota"):
                r["nota"] = nota
    return sorted(vistos.values(), key=lambda r: (I.clave_orde(r["forma"]), r["tipo"]))


def importar_onomastica(capa: str, rutas: list[Path]):
    vistos = {}
    for ruta in rutas:
        fonte = fonte_de(ruta)
        for palabra, _, etiquetas, nota in liñas(ruta):
            nome = frase_ngrama(etiquetas) or palabra
            if palabra.islower() and nome == palabra:
                continue
            tipo = next((e[3:] for e in etiquetas if e.startswith("po:")), "nome_propio")
            clave = (nome, tipo)
            r = vistos.setdefault(clave, {"nome": nome, "tipo": tipo, "capa": capa, "fontes": []})
            if fonte not in r["fontes"]:
                r["fontes"].append(fonte)
            if nota and not r.get("nota") and not nota.startswith("http"):
                r["nota"] = nota
    return sorted(vistos.values(), key=lambda r: (I.clave_orde(r["nome"]), r["tipo"]))


def importar_codigos(capa: str, rutas: list[Path]):
    saida = []
    for ruta in rutas:
        tipo = ruta.relative_to(SRC).parts[0]
        for palabra, _, _, nota in liñas(ruta):
            saida.append({"codigo": palabra, "tipo": tipo, "capa": capa, "nota": nota.rstrip(".")})
    return saida


def main() -> None:
    config = json.loads((RAIZ / "fontes" / "capas.json").read_text(encoding="utf-8"))["capas"]
    pedidas = sys.argv[1:] or list(config)
    SAIDA.mkdir(parents=True, exist_ok=True)
    frecuencias = I.ler_frecuencias(I.CACHE / "frecuencias-opensubtitles" / "gl_full.txt")
    correccions = json.loads((I.DATOS / "correccions" / "conxugacions.json").read_text(encoding="utf-8"))
    referencia = json.loads((I.DATOS / "correccions" / "referencia.json").read_text(encoding="utf-8"))
    referencia.pop("_descricion", None)
    referencia = compostos.con_compostos(referencia)
    ruta_rag = I.DATOS / "referencia-rag.json"
    if ruta_rag.exists():      # o conxugador da RAG manda sobre todo o anterior
        rag = json.loads(ruta_rag.read_text(encoding="utf-8"))
        rag.pop("_descricion", None)
        referencia.update(rag)

    config = {capa: cfg for capa, cfg in config.items() if "modulos" in cfg}   # as de «script» van á parte
    pedidas = [c for c in pedidas if c in config]
    rutas_capa = {capa: [r for m in cfg["modulos"] for r in ficheiros(m)] for capa, cfg in config.items()}
    lexicas = [c for c in config if config[c]["tipo"] == "lexico"]
    h = Hunspell(I.HUNSPELL / "gl.aff", [r for c in lexicas for r in rutas_capa[c]])

    xa_vistos = {json.loads(l)["id"] for l in (I.DATOS / "lemas.jsonl").open(encoding="utf-8")}
    for capa in config:   # as léxicas en orde: a primeira que teña un lema quédao
        cfg = config[capa]
        if cfg["tipo"] != "lexico":
            continue
        rexistros = importar_lexico(capa, rutas_capa[capa], h, frecuencias, correccions, referencia, xa_vistos)
        if capa in pedidas:
            escribir(capa, rexistros)

    for capa in pedidas:
        cfg = config[capa]
        if cfg["tipo"] == "siglas":
            escribir(capa, importar_siglas(capa, rutas_capa[capa]))
        elif cfg["tipo"] == "onomastica":
            escribir(capa, importar_onomastica(capa, rutas_capa[capa]))
        elif cfg["tipo"] == "codigos":
            escribir(capa, importar_codigos(capa, rutas_capa[capa]))


def escribir(capa: str, rexistros: list[dict]) -> None:
    with (SAIDA / f"{capa}.jsonl").open("w", encoding="utf-8") as fh:
        for r in rexistros:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    verbos = sum(1 for r in rexistros if r.get("categoria") == "verbo")
    baleiras = [r["lema"] for r in rexistros if r.get("baleiras")]
    extra = f", {verbos} verbos" if verbos else ""
    if baleiras:
        extra += f", {len(baleiras)} con celas baleiras: {', '.join(baleiras[:12])}"
    print(f"datos/capas/{capa}.jsonl: {len(rexistros)} rexistros{extra}")


if __name__ == "__main__":
    main()
