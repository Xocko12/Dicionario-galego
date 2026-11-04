"""Táboas de referencia dos verbos compostos, derivadas das do verbo base.

«manter» conxúgase como «ter», «convir» como «vir», «supor» como «pór»… As
listas son explícitas porque a terminación non abonda: «servir» non é composto
de «vir» nin «bater» de «ter». O prefixo engádese a cada forma e o til
recalcúlase coas regras das Normas (acentuacion.py): ten → mantén, di → predí,
fai → desfai, pór → supor.
"""

from __future__ import annotations

import acentuacion as AC
import conxugacion as C

COMPOSTOS = {
    "ter": ["abster", "ater", "conter", "deter", "entreter", "manter", "obter", "reter", "soster"],
    "vir": ["advir", "avir", "contravir", "convir", "desavir", "desconvir", "devir", "intervir",
            "previr", "provir", "reconvir", "sobrevir"],
    "pór": ["antepor", "apor", "arrepor", "compor", "contrapor", "depor", "desapor", "descompor", "dispor",
            "empor", "expor", "impor", "indispor", "interpor", "opor", "pospor", "precompor", "predispor",
            "presupor", "propor", "recompor", "reimpor", "repor", "sobreexpor", "sobrepor", "subexpor",
            "superpor", "supor", "traspor", "xustapor"],
    "poñer": ["antepoñer", "apoñer", "arrepoñer", "compoñer", "contrapoñer", "depoñer", "desapoñer",
              "descompoñer", "dispoñer", "empoñer", "expoñer", "impoñer", "indispoñer", "interpoñer", "opoñer",
              "pospoñer", "precompoñer", "predispoñer", "presupoñer", "propoñer", "recompoñer", "reimpoñer",
              "repoñer", "sobreexpoñer", "sobrepoñer", "subexpoñer", "superpoñer", "supoñer", "traspoñer",
              "xustapoñer"],
    "facer": ["afacer", "contrafacer", "desafacer", "desfacer", "rarefacer", "refacer", "satisfacer", "tumefacer"],
    "dicir": ["contradicir", "desdicir", "predicir"],
    # traer: os compostos teñen pretérito regular (atraín, contraeu), non trouxen; non se derivan
    "valer": ["equivaler", "prevaler"],
    "ver": ["antever", "entrever", "prever", "rever"],
    "oír": ["desoír", "entreoír"],
    "saír": ["sobresaír"],
    "caer": ["decaer", "recaer"],
    # ler/crer (rele ou relé? descre ou descré?) quedan fóra ata confirmalo coa RAG
    "rir": ["sorrir"],
    "seguir": ["conseguir", "perseguir", "proseguir"],
    "sentir": ["asentir", "consentir", "presentir", "resentir"],
    "pedir": ["despedir", "expedir", "impedir"],
    "construír": ["reconstruír"],
}


def compor(prefixo: str, forma: str) -> str:
    """Prefixo + forma, co til recalculado (a sílaba tónica non cambia)."""
    vogal = AC.vogal_tonica(forma)
    if vogal is None:
        return prefixo + forma
    return AC.acentuar(AC.sen_til(prefixo) + AC.sen_til(forma), len(prefixo) + vogal)


def derivar(referencia: dict) -> dict:
    """Referencia dos compostos a partir da dos verbos base (só os que non
    teñan xa referencia propia)."""
    saida = {}
    for base, compostos in COMPOSTOS.items():
        if base not in referencia:
            continue
        for composto in compostos:
            if composto in referencia:
                continue
            prefixo = composto[: len(composto) - len(base)]
            assert AC.sen_til(composto) == AC.sen_til(prefixo + base), composto   # antepor / pór
            celas = {}
            for clave, valor in referencia[base]["celas"].items():
                if valor and isinstance(valor[0], list):
                    celas[clave] = [[compor(prefixo, f) for f in cela] for cela in valor]
                else:
                    celas[clave] = [compor(prefixo, f) for f in valor]
            saida[composto] = {"nota": f"Derivada de {base} (prefixo «{prefixo}»).", "celas": celas}
    return saida


def con_compostos(referencia: dict) -> dict:
    """A referencia completa: a escrita a man máis a derivada para os compostos."""
    completa = dict(referencia)
    completa.update(derivar(referencia))
    return completa


if __name__ == "__main__":
    for b, f, e in (("man", "ten", "mantén"), ("man", "tes", "mantés"), ("con", "vén", "convén"), ("con", "ven", "convén"),
                    ("su", "pon", "supón"), ("su", "pór", "supor"), ("pre", "di", "predí"), ("des", "fai", "desfai"),
                    ("des", "fas", "desfás"), ("pre", "ve", "prevé"), ("pre", "ven", "prevén"), 
                    ("sobre", "saio", "sobresaio"), ("sor", "rin", "sorrín"), ("sobre", "saír", "sobresaír")):
        print(b + "+" + f, "->", compor(b, f), "✓" if compor(b, f) == e else f"✗ (esperado {e})")
