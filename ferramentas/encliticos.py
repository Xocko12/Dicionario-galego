"""Formas verbais con pronomes enclíticos de uso real (dime, díxocho, esqueceuseme).

Hunspell-gl xera todas as combinacións teóricas de verbo + pronomes (máis de
160 millóns, moitas tan forzadas como «falándochello»). Aquí só se gardan as que:

  1. aparecen no corpus de frecuencias (uso real),
  2. non son xa unha forma simple do catálogo («abríramos» é antepretérito,
     non «abríra» + «mos»), nin unha grafía antiga dunha («poderíamos»),
  3. a parte verbal coincide coa táboa corrixida do verbo,
  4. levan un pronome, unha contracción de dativo + acusativo (mo, cho, llo,
     nolo, volo, llelo) ou «se» + dativo (esqueceuseme).

Úsase desde importar.py e xera datos/encliticos.jsonl.
"""

from __future__ import annotations

import re

import conxugacion as C

# pronome enclítico segundo a descrición de Hunspell-gl (campo pa:)
_PERSOA_DATIVO = {"P1": "me", "P2": "che", "P3": "lle", "P4": "nos", "P5": "vos", "P6": "lles"}
_PERSOA_ACUSATIVO = {"P1": "me", "P2": "te", "P4": "nos", "P5": "vos"}
_PERSOA_REFLEXIVO = {"P1": "me", "P2": "te", "P3": "se", "P4": "nos", "P5": "vos", "P6": "se"}
_ACUSATIVO_P3 = {("masculino", "singular"): "o", ("feminino", "singular"): "a",
                 ("masculino", "plural"): "os", ("feminino", "plural"): "as"}
# forma do acusativo P3 ao final da palabra (para as contraccións: cho, cha, chos, chas)
_FIN_ACUSATIVO = (("os", "os"), ("as", "as"), ("o", "o"), ("a", "a"))


def _pronome(parte: str, forma: str) -> str | None:
    parte = parte.replace("_", " ")
    persoa = re.search(r"P[1-6]", parte)
    persoa = persoa.group(0) if persoa else None
    if parte.startswith("reflexivo"):
        return _PERSOA_REFLEXIVO.get(persoa)
    if parte.startswith("dativo"):            # "dativo P2", "dativo / acusativo P1"
        return _PERSOA_DATIVO.get(persoa)
    if parte.startswith("acusativo"):
        if persoa != "P3":
            return _PERSOA_ACUSATIVO.get(persoa)
        for (xenero, numero), pron in _ACUSATIVO_P3.items():
            if xenero in parte and numero in parte:
                return pron
        for fin, pron in _FIN_ACUSATIVO:    # contraccións: o xénero vese na forma
            if forma.endswith(fin):
                return pron
    return None


def pronomes(morph: tuple[str, ...], forma: str) -> list[str] | None:
    """Lista de pronomes dunha forma con enclíticos, ou None se a combinación
    non se admite (máis de dous pronomes, dous dativos...)."""
    texto = " ".join(morph)
    if "pa:" not in texto:
        return None
    descricion = texto.split("pa:", 1)[1]
    # quitar "pronome persoal enclítico [monosílabo P3 / P6 transitiva]"
    descricion = re.sub(r"^.*?(?=\b(dativo|acusativo|reflexivo)\b)", "", descricion)
    descricion = re.sub(r"\balomorfo\b|\btras .*$", "", descricion)
    partes = [p.strip() for p in descricion.split("+") if p.strip()]
    lista = [_pronome(p, forma) for p in partes]
    if not lista or None in lista:
        return None
    tipos = [p.split()[0] for p in partes]
    if len(lista) == 1:
        return lista
    if len(lista) == 2:
        if tipos[0] == "dativo" and tipos[1] == "acusativo" and lista[1] in ("o", "a", "os", "as"):
            return lista                     # mo, cho, llo, nolo, volo, llelo
        if tipos[0] == "reflexivo" and lista[0] == "se" and tipos[1] == "dativo":
            return lista                     # seme, seche, selle, senos, sevos, selles
    return None


def _base_coherente(forma: str, taboa: dict, base: str) -> bool:
    """A parte verbal ten que coincidir coa cela da táboa (xa corrixida):
    "díxenlle" -> pretérito P1 "dixen"; "falalo" -> infinitivo "falar"
    (o pronome pode quitar o -r ou -s final)."""
    clave, _, persoa = base.rpartition(".")
    if persoa in C.PERSOAS:
        cela = taboa[clave][C.PERSOAS.index(persoa)]
    else:
        cela = taboa.get(base, [])
    sen_til = C.sen_acentos(forma)
    return any(sen_til.startswith(C.sen_acentos(f)[:-1]) for f in cela)


def buscar(h, lemas_verbos: set[str], admitir, corpus: dict[str, int], formas_simples: set[str],
           taboas: dict[str, dict]) -> list[dict]:
    """Formas con enclíticos atestadas no corpus. `admitir(entrada, lema)` como en
    conxugacion.taboas_desde_hunspell. `taboas` son as táboas xa corrixidas."""
    # O corpus ten grafías anteriores a 2003 das P4 e P5 do copretérito,
    # antepretérito e pospretérito ("dixéramos", "poderíamos"), que non son
    # verbo + "mos". Só esas: "chámase" (chama + se) non é "chamase".
    grafias_antigas = set()
    for taboa in taboas.values():
        for clave in ("indicativo.copreterito", "indicativo.antepreterito", "indicativo.pospreterito"):
            for p in (3, 4):
                grafias_antigas.update(C.sen_acentos(f) for f in taboa[clave][p])
    prefixos = {palabra[:i] for palabra in corpus for i in range(1, len(palabra) + 1)}

    def continuar(intermedia: str) -> bool:
        # os sufixos de pronome quitan como moito unha letra
        return intermedia[:-1] in prefixos

    def omitir(afixo) -> bool:
        return False

    alomorfos: dict[str, str] = {}
    for e in h.entries:
        if C.es_verbo(h, e) and e.word in lemas_verbos and admitir(e, e.word):
            for al in e.fields("al"):
                alomorfos.setdefault(al, e.word)

    atopadas: dict[tuple, dict] = {}
    for e in h.entries:
        if C.es_verbo(h, e):
            lema = e.word
        else:
            lema = (e.fields("st") or [alomorfos.get(e.word) if h.needaffix in e.flags else None])[0]
        if lema not in lemas_verbos or not admitir(e, lema):
            continue
        for f in h.expand(e, omitir, continue_from=continuar):
            if f.form not in corpus or f.form in formas_simples or C.sen_acentos(f.form) in grafias_antigas:
                continue
            lista = pronomes(f.morph, f.form)
            if not lista:
                continue
            base = [b for b in (f"{clave}.{C.PERSOAS[p]}" if p is not None else clave
                                for clave, p in C.celas(f.morph))
                    if _base_coherente(f.form, taboas[lema], b)]
            if not base:
                continue
            clave = (f.form, lema, tuple(lista))
            rexistro = atopadas.setdefault(clave, {"forma": f.form, "lema": lema, "base": [],
                                                   "pronomes": lista, "frecuencia": corpus[f.form]})
            for b in base:
                if b not in rexistro["base"]:
                    rexistro["base"].append(b)
    return sorted(atopadas.values(), key=lambda r: (C.sen_acentos(r["forma"]), r["forma"], r["lema"]))
