"""Acentuación do galego, implementada de maneira independente de Hunspell.

Serve para comprobar as formas con enclíticos: a sílaba tónica da forma verbal
non cambia ao engadir pronomes, así que o til da palabra resultante pode
predicirse coas Normas (RAG/ILG 2003, cap. de acentuación):

  - agudas: til se rematan en vogal, -n, -s ou -ns, agás se rematan en
    ditongo decrecente (falou, cantei, papeis);
  - graves: til se rematan en consoante distinta de -n/-s ou en ditongo
    decrecente (amábeis);
  - esdrúxulas e sobresdrúxulas: sempre;
  - hiato: i/u tónicos xunto a outra vogal levan sempre til (saía, oílo);
  - til diacrítico: non se predí aquí (dá, é, vén...).

Uso: python3 ferramentas/acentuacion.py  -> comproba dist/dicionario.sqlite
"""

from __future__ import annotations

import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

FORTES = set("aeoáéóíú")           # vogais que forman sílaba de seu; í/ú tónicas tamén
DEBILES = set("iuü")
VOGAIS = FORTES | DEBILES
CON_TIL = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"}
PON_TIL = {v: k for k, v in CON_TIL.items()}
DITONGOS_DECRECENTES = ("ai", "ei", "oi", "ui", "au", "eu", "ou", "iu")


def sen_til(p: str) -> str:
    return "".join(CON_TIL.get(c, c) for c in p)


def _u_muda(palabra: str, i: int) -> bool:
    """O u de que/qui/gue/gui non soa (agás con diérese)."""
    return (palabra[i] == "u" and i > 0 and palabra[i - 1] in "qg"
            and i + 1 < len(palabra) and sen_til(palabra[i + 1]) in "ei")


def silabas(palabra: str, tonica: int | None = None) -> list[list[int]]:
    """Índices das vogais de cada sílaba (os núcleos). `tonica` é a posición
    da vogal tónica: un i/u tónico xunto a outra vogal fai hiato (sa-í-a)."""
    def forte(i: int) -> bool:
        return palabra[i] in FORTES or i == tonica

    def debil_atona(i: int) -> bool:
        return palabra[i] in DEBILES and not forte(i)

    def ditongo(x: int, y: int) -> bool:
        # débil átona + forte (ia, ue), forte + débil átona (ai, ou),
        # ou dúas débiles coa segunda átona (iu, ui: viu, muito; ruín é hiato)
        if debil_atona(x) and palabra[y] in FORTES:
            return True
        if palabra[x] in FORTES and debil_atona(y):
            return True
        return palabra[x] in DEBILES and palabra[y] in DEBILES and debil_atona(y)

    nucleos: list[list[int]] = []
    i = 0
    n = len(palabra)
    while i < n:
        if palabra[i] not in VOGAIS or _u_muda(palabra, i):
            i += 1
            continue
        grupo = [i]
        if i + 1 < n and palabra[i + 1] in VOGAIS and not _u_muda(palabra, i + 1) and ditongo(i, i + 1):
            grupo.append(i + 1)
            i += 1
            # tritongo: débil átona + forte + débil átona (uai, iei)
            if (i + 1 < n and palabra[i + 1] in VOGAIS and debil_atona(i + 1)
                    and palabra[i] in FORTES and debil_atona(i - 1)):
                grupo.append(i + 1)
                i += 1
        nucleos.append(grupo)
        i += 1
    return nucleos


def vogal_tonica(palabra: str) -> int | None:
    """Posición da vogal tónica dunha palabra ben acentuada."""
    for i, c in enumerate(palabra):
        if c in CON_TIL:
            return i
    sil = silabas(palabra)
    if not sil:
        return None
    if len(sil) == 1:
        k = 0
    else:
        fin = palabra[-1]
        base = palabra[:-1] if fin in "ns" else palabra
        if fin in VOGAIS or fin in "ns":
            ditongo = any(base.endswith(d) for d in DITONGOS_DECRECENTES) and not _u_muda(palabra, len(base) - 2)
            k = len(sil) - 1 if ditongo else len(sil) - 2
        else:
            k = len(sil) - 1
    grupo = sil[k]
    fortes = [i for i in grupo if palabra[i] in FORTES]
    return fortes[0] if fortes else grupo[0]


def acentuar(palabra_sen_til: str, vogal: int) -> str:
    """Pon o til que corresponde á palabra (sen tiles) coa vogal tónica en `vogal`."""
    p = palabra_sen_til
    sil = silabas(p, vogal)
    k = next((j for j, g in enumerate(sil) if vogal in g), None)
    if k is None:
        return p
    grupo = sil[k]
    desde_fin = len(sil) - 1 - k
    # i/u tónicos xunto a unha vogal que non forma ditongo con eles (sa-í-a,
    # cons-tru-íu): levan til sempre
    hiato = (p[vogal] in "iu"
             and ((vogal > 0 and p[vogal - 1] in VOGAIS and vogal - 1 not in grupo and not _u_muda(p, vogal - 1))
                  or (vogal + 1 < len(p) and p[vogal + 1] in VOGAIS and vogal + 1 not in grupo)))
    fin = p[-1]
    base = p[:-1] if fin in "ns" else p
    # ditongo decrecente final (falou, cantei); o u de que/qui/gue/gui non conta (caciquís)
    remata_ditongo = any(base.endswith(d) for d in DITONGOS_DECRECENTES) and not _u_muda(p, len(base) - 2)
    if hiato or desde_fin >= 2:
        leva = True
    elif desde_fin == 1:
        leva = not (fin in VOGAIS or fin in "ns") or remata_ditongo
    else:
        leva = (fin in VOGAIS or fin in "ns") and not remata_ditongo
    if not leva:
        return p
    return p[:vogal] + PON_TIL.get(p[vogal], p[vogal]) + p[vogal + 1:]


def predicir(base: str, pronomes: str) -> str:
    """Forma esperada de base + pronomes, recortando o -r/-s/-n final se fai falta."""
    return sorted(predicir_todas(base, pronomes), key=lambda f: f != sen_til(base) + pronomes)[-1]


def predicir_todas(base: str, pronomes: str) -> set[str]:
    """Formas posibles: coa base enteira ou sen o -r/-s/-n final."""
    vogal = vogal_tonica(base)
    raiz = sen_til(base)
    saida = {acentuar(raiz + pronomes, vogal)}
    if raiz[-1:] in "rsn" and vogal is not None and vogal < len(raiz) - 1:
        saida.add(acentuar(raiz[:-1] + pronomes, vogal))
    return saida


# -- comprobación das formas sistemáticas ------------------------------------

def comprobar(db_path: Path, limite: int = 0) -> None:
    db = sqlite3.connect(db_path)
    celas: dict[tuple, list[str]] = defaultdict(list)
    for forma, lema_id, trazo in db.execute("select forma, lema_id, trazo from formas"):
        celas[(lema_id, trazo)].append(forma)
    acordo = 0
    desacordos: dict[str, list] = defaultdict(list)
    sql = "select forma, lema_id, base, pronomes from encliticos where orixe='sistematica'"
    if limite:
        sql += f" limit {limite}"
    for forma, lema_id, bases, pronomes in db.execute(sql):
        candidatas = [b for trazo in bases.split(",") for b in celas.get((lema_id, trazo), [])]
        if not candidatas:
            desacordos["sen forma base"].append((forma, lema_id, bases))
            continue
        esperadas = set()
        base_usada = None
        for base in candidatas:
            cola = _cola(sen_til(forma), sen_til(base))
            if cola is None:
                continue
            base_usada = base_usada or base
            esperadas |= predicir_todas(base, cola)
        if base_usada is None:
            desacordos["base non recoñecible"].append((forma, candidatas))
        elif forma in esperadas:
            acordo += 1
        else:
            desacordos[_clasificar(forma, sorted(esperadas)[0], base_usada)].append(
                (forma, sorted(esperadas), base_usada, pronomes))
    total = acordo + sum(len(v) for v in desacordos.values())
    print(f"{total} formas sistemáticas: {acordo} coinciden coa acentuación predita ({100 * acordo / total:.2f} %)")
    for clase, lista in sorted(desacordos.items(), key=lambda x: -len(x[1])):
        print(f"\n## {clase}: {len(lista)}")
        for x in lista[:15]:
            print("  ", x)
        verbos = Counter(x[2] if len(x) > 2 else str(x[1]) for x in lista)
        print("   bases:", ", ".join(f"{v} ({n})" for v, n in verbos.most_common(10)))


def _cola(forma: str, base: str) -> str | None:
    """Pronomes engadidos: a forma menos a base (que pode perder r/s/n finais)."""
    for recorte in ("", base[-1:] if base[-1:] in "rsn" else ""):
        raiz = base[: len(base) - len(recorte)]
        if forma.startswith(raiz) and len(forma) > len(raiz):
            return forma[len(raiz):]
    return None


def _clasificar(forma: str, esperada: str, base: str) -> str:
    if sen_til(forma) != sen_til(esperada):
        return "letras distintas"
    if len(sen_til(base)) <= 3 and any(c in CON_TIL for c in base):
        return "til diacrítico na base"
    if forma == sen_til(forma):
        return "Hunspell sen til, predito con til"
    if esperada == sen_til(esperada):
        return "Hunspell con til, predito sen til"
    return "til noutra vogal"


if __name__ == "__main__":
    comprobar(RAIZ / "dist" / "dicionario.sqlite", int(sys.argv[1]) if len(sys.argv) > 1 else 0)
