"""Formas que as regras de Hunspell-gl aceptan pero que, segundo o conxugador da
RAG, están mal: para marcalas como prohibidas (FORBIDDENWORD) no corrector.

Só se prohibe unha forma cando a RAG dá outra forma *na mesma cela* (tempo e
persoa) do mesmo verbo: así «cubrido» (RAG: cuberto), «conviron» (conviñeron),
«éras» (eras), «bendizas» (bendigas). Non se prohiben as formas das celas que a
RAG deixa baleiras (verbos unipersoais) nin as que son forma doutro lema.
"""

from __future__ import annotations

import json
from pathlib import Path

import conxugacion as C
import importar as I
from hunspell import Hunspell

RAIZ = Path(__file__).resolve().parent.parent


def calcular(lemas: list[dict], conx: dict, encl: list[dict]) -> dict[str, str]:
    """{forma prohibida: verbo}. `conx` son as táboas finais (coa referencia da RAG)."""
    rag = set(json.load((I.DATOS / "referencia-rag.json").open(encoding="utf-8"))) - {"_descricion"}
    mods = I.modulos()
    h = Hunspell(I.HUNSPELL / "gl.aff", [r for _, _, r in mods])
    omitir = C.omitir_encliticos(h)
    taboas = {lema: v["taboa"] for lema, v in conx.items()}
    alomorfos: dict[str, str] = {}
    for e in h.entries:
        if C.es_verbo(h, e) and e.word in taboas:
            for a in e.fields("al"):
                alomorfos.setdefault(a, e.word)
    outras: set[str] = set()
    for r in lemas:
        if r["categoria"] != "verbo":
            outras.add(r["lema"])
            outras.update(f for x in r.get("formas", {}).values() for f in x)
    outras.update(r["forma"] for r in encl)
    nosas = {f for t in taboas.values() for f, _, _ in C.formas(t)}
    prohibidas: dict[str, str] = {}
    for e in h.entries:
        if C.es_verbo(h, e):
            lema = e.word
        else:
            lema = (e.fields("st") or [alomorfos.get(e.word) if h.needaffix in e.flags else None])[0]
        if lema not in taboas or lema not in rag:
            continue
        t = taboas[lema]
        for f in h.expand(e, omitir):
            if f.form in nosas or f.form in outras:
                continue
            for clave, p in C.celas(f.morph):
                cela = t[clave] if p is None else t[clave][p]
                if cela and f.form not in cela:
                    prohibidas.setdefault(f.form, lema)
    return prohibidas
