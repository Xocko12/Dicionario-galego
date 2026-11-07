"""Táboas de conxugación a partir das etiquetas morfolóxicas de Hunspell.

As etiquetas de Proxecto Trasno seguen a terminoloxía da RAG
(copretérito, antepretérito, pospretérito...). Aquí convértense nunha
táboa con claves estables:

    {"indicativo.presente": ["falo", "falas", ...], ...}

Cada cela é unha lista de formas (pode haber variantes, p. ex. "fixeches").
"""

from __future__ import annotations

import re
import unicodedata

PERSOAS = ["P1", "P2", "P3", "P4", "P5", "P6"]

# Orde de presentación das táboas.
TEMPOS = [
    ("indicativo.presente", "Presente"),
    ("indicativo.copreterito", "Copretérito"),
    ("indicativo.preterito", "Pretérito"),
    ("indicativo.antepreterito", "Antepretérito"),
    ("indicativo.futuro", "Futuro"),
    ("indicativo.pospreterito", "Pospretérito"),
    ("subxuntivo.presente", "Presente de subxuntivo"),
    ("subxuntivo.preterito", "Pretérito de subxuntivo"),
    ("subxuntivo.futuro", "Futuro de subxuntivo"),
    ("imperativo", "Imperativo"),
    ("infinitivo.conxugado", "Infinitivo conxugado"),
]
FORMAS_NOMINAIS = ["infinitivo", "xerundio", "participio"]

# Nome do tempo en Hunspell -> clave propia.
_TEMPO_HUNSPELL = {
    "presente": "indicativo.presente",
    "copretérito": "indicativo.copreterito",
    "pretérito": "indicativo.preterito",
    "antepretérito": "indicativo.antepreterito",
    "futuro": "indicativo.futuro",
    "pospretérito": "indicativo.pospreterito",
    "subxuntivo presente": "subxuntivo.presente",
    "subxuntivo pretérito": "subxuntivo.preterito",
    "subxuntivo copretérito": "subxuntivo.preterito",
    "subxuntivo futuro": "subxuntivo.futuro",
    "imperativo": "imperativo",
    "infinitivo": "infinitivo.conxugado",
}

_PERSOA_RE = re.compile(r"\bP([1-6])\b")
_ACENTOS = set("áéíóú")


def _texto_is(morph: tuple[str, ...]) -> str:
    texto = " ".join(m for m in morph if m != ".")
    partes = re.findall(r"is:(.*?)(?=\s+[a-z]{2}:|$)", texto)
    return " / ".join(p.strip() for p in partes)


def celas(morph: tuple[str, ...]) -> list[tuple[str, int | None]]:
    """Converte etiquetas como 'is:presente P3 / imperativo P2' en celas.

    Devolve [(clave, índice_persoa | None)]; None para formas nominais.
    """
    texto = _texto_is(morph)
    # "[ + acusativo P3 ... ]" e "+ enclítico" describen combinacións con
    # pronomes, non a forma en si.
    anterior = None
    while anterior != texto:                 # corchetes aniñados: [ + [reflexivo [ + dativo]]]
        anterior = texto
        texto = re.sub(r"\[[^\[\]]*\]", "", texto)
    texto = re.sub(r"\+[^/]*", "", texto).strip()
    texto = texto.replace("partiticipio", "participio")        # erro tipográfico de Hunspell-gl
    texto = texto.replace("presente impersoal", "presente P3")  # hai (haber)
    # "infinitivo P1 e P3", "copretérito P1 e P3" (formas con enclíticos: darlle,
    # dábame) son dúas celas co mesmo tempo.
    texto = re.sub(r"\bP([1-6]) e P([1-6])\b", r"P\1 / P\2", texto)
    if not texto:
        return []
    partes = [p.strip() for p in texto.split("/")]
    # Cada parte pode ter tempo, persoa ou ambos. Completamos o que falte:
    # "subxuntivo presente P1 / P3" -> o P3 herda o tempo anterior;
    # "infinitivo / subxuntivo futuro P2" -> o infinitivo herda a persoa seguinte.
    analizadas = []
    for parte in partes:
        m = _PERSOA_RE.search(parte)
        persoa = int(m.group(1)) - 1 if m else None
        tempo = _PERSOA_RE.sub("", parte).strip() or None
        analizadas.append([tempo, persoa])
    for i, (tempo, persoa) in enumerate(analizadas):
        if tempo is None and i > 0:
            analizadas[i][0] = analizadas[i - 1][0]
    for i in range(len(analizadas) - 2, -1, -1):
        if analizadas[i][1] is None and analizadas[i][0] not in ("xerundio", "participio"):
            analizadas[i][1] = analizadas[i + 1][1]

    out = []
    for tempo, persoa in analizadas:
        if tempo in ("xerundio", "participio"):
            out.append((tempo, None))
        elif tempo in _TEMPO_HUNSPELL and persoa is not None:
            out.append((_TEMPO_HUNSPELL[tempo], persoa))
    return out


def ten_acento(palabra: str) -> bool:
    return any(c in _ACENTOS for c in palabra)


def sen_acentos(palabra: str) -> str:
    nfd = unicodedata.normalize("NFD", palabra)
    return unicodedata.normalize("NFC", "".join(c for c in nfd if unicodedata.category(c) != "Mn"))


def taboa_baleira(lema: str) -> dict:
    taboa = {clave: [[] for _ in PERSOAS] for clave, _ in TEMPOS}
    taboa["infinitivo"] = [lema]
    taboa["xerundio"] = []
    taboa["participio"] = []
    return taboa


def engadir(taboa: dict, clave: str, persoa: int | None, forma: str) -> None:
    cela = taboa[clave] if persoa is None else taboa[clave][persoa]
    if forma not in cela:
        cela.append(forma)


def _derivar(cela_orixe, cela_destino, quitar: str, poñer: str) -> None:
    """Engade á cela de destino as formas derivadas que lle falten."""
    for forma in cela_orixe:
        if forma.endswith(quitar) if quitar else True:
            nova = (forma[: len(forma) - len(quitar)] if quitar else forma) + poñer
            if nova not in cela_destino:
                cela_destino.append(nova)


_IMPERATIVO_SEN_TIL = {"vén": "ven"}


def completar(taboa: dict, lema: str) -> None:
    """Enche ocos que Hunspell non etiqueta, con regras que valen para todos os verbos.

    - infinitivo conxugado P1/P3 = infinitivo;
    - copretérito e antepretérito: P1 = P3 = P2 sen -s (e viceversa);
    - futuro de subxuntivo: P1 = P3 = P2 sen -es; P6 = P2 con -en;
    - imperativo P2: o de Hunspell ou, se falta, a P3 do presente;
      o imperativo só ten P2 e P5 (e a P4 «vamos» de ir);
    - futuro de subxuntivo baleiro = infinitivo conxugado (pretérito regular);
    - os verbos unipersoais (chover) non se completan.
    """
    inf = taboa["infinitivo.conxugado"]
    for p in (0, 2):
        if not inf[p]:
            inf[p].append(lema)
    imp = taboa["imperativo"]
    if unipersoal(taboa):
        taboa["imperativo"] = [[] for _ in PERSOAS]
        fut = taboa["subxuntivo.futuro"]
        for p in (2, 5):
            if not fut[p]:
                fut[p] = list(inf[p])
        return
    fut = taboa["subxuntivo.futuro"]
    if not any(fut):
        # cos pretéritos regulares coincide co infinitivo conxugado
        taboa["subxuntivo.futuro"] = [list(c) for c in inf]
    for clave in ("indicativo.copreterito", "indicativo.antepreterito"):
        t = taboa[clave]
        _derivar(t[1], t[0], "s", "")
        _derivar(t[1], t[2], "s", "")
        _derivar(t[0] or t[2], t[1], "", "s")
    fut = taboa["subxuntivo.futuro"]
    _derivar(fut[1], fut[0], "es", "")
    _derivar(fut[1], fut[2], "es", "")
    _derivar(fut[1], fut[5], "es", "en")
    _derivar(fut[5], fut[0], "en", "")
    _derivar(fut[5], fut[2], "en", "")
    # Imperativo P2: o que dan as regras de Hunspell (durme, sube, sigue, fire:
    # o conxugador da RAG confírmaos); se falta, a P3 do presente. O monosílabo
    # "vén" perde o til diacrítico: "ven".
    imp = taboa["imperativo"]
    if not imp[1]:
        imp[1] = [_IMPERATIVO_SEN_TIL.get(f, f) for f in taboa["indicativo.presente"][2]]
    # O imperativo só ten P2 e P5; a P4 consérvase se Hunspell a dá (só «vamos», de ir).
    for p in (0, 2, 5):
        imp[p] = []


def aplicar_correccion(taboa: dict, correccion: dict) -> list[str]:
    """Substitúe celas enteiras polas da corrección manual.

    Claves admitidas: "indicativo.presente" (lista de 6 celas),
    "indicativo.presente.P3" (unha cela), "participio", "xerundio".
    Devolve a lista de claves corrixidas.
    """
    feitas = []
    for clave, valor in correccion.get("celas", {}).items():
        base, _, persoa = clave.rpartition(".")
        if persoa in PERSOAS and base in taboa:
            taboa[base][PERSOAS.index(persoa)] = list(valor)
        elif clave in ("participio", "xerundio", "infinitivo"):
            taboa[clave] = list(valor)
        elif clave in taboa and len(valor) == 6:
            taboa[clave] = [list(c) if isinstance(c, list) else [c] for c in valor]
        else:
            raise ValueError(f"Clave de corrección descoñecida: {clave}")
        feitas.append(clave)
    return feitas


_TIL_MONOSILABOS = {"pos": "pós", "pon": "pón"}

# Verbo base -> (terminación dos compostos, compostos admitidos ou None = todos).
# Para ler e crer lístanse: hai moitos verbos en -ler que non son compostos (valer, moler).
COMPOSTOS = {
    "pór": ("por", None),
    "dicir": ("dicir", None),
    "ler": ("ler", {"reler", "trasler"}),
    "crer": ("crer", {"descrer"}),
}
# bendicir e maldicir teñen tamén formas regulares (bendicín, bendicirei): non se derivan.
NON_DERIVAR = {"bendicir", "maldicir"}


def correccion_derivada(lema: str, correccions: dict) -> dict | None:
    """Corrección dun composto (supor, predicir, reler) a partir da do verbo base.

    Os monosílabos levan til ao ir compostos: pon -> supón, pos -> supós.
    """
    if lema in correccions or lema in NON_DERIVAR:
        return None
    for base, (final, admitidos) in COMPOSTOS.items():
        if lema == base or not lema.endswith(final) or base not in correccions:
            continue
        if admitidos is not None and lema not in admitidos:
            continue
        prefixo = lema[: -len(final)]

        def compor(forma):
            return prefixo + _TIL_MONOSILABOS.get(forma, forma)

        celas_novas = {}
        for clave, valor in correccions[base]["celas"].items():
            if valor and isinstance(valor[0], list):
                celas_novas[clave] = [[compor(f) for f in cela] for cela in valor]
            else:
                celas_novas[clave] = [compor(f) for f in valor]
        return {"nota": f"Derivada de {base} (prefixo '{prefixo}').", "celas": celas_novas}
    return None


def aplicar_referencia(taboa: dict, referencia: dict) -> list[str]:
    """Como aplicar_correccion, pero devolve só as celas que cambiaron de
    verdade (as que Hunspell tiña distintas). Compara como conxuntos."""
    cambiadas = []
    for clave, valor in referencia.get("celas", {}).items():
        base, _, persoa = clave.rpartition(".")
        if persoa in PERSOAS:
            actual = taboa[base][PERSOAS.index(persoa)]
            if set(actual) != set(valor):
                taboa[base][PERSOAS.index(persoa)] = list(valor)
                cambiadas.append(clave)
        elif clave in ("participio", "xerundio", "infinitivo"):
            if set(taboa[clave]) != set(valor):
                taboa[clave] = list(valor)
                cambiadas.append(clave)
        elif clave in taboa and len(valor) == 6:
            for p, cela in enumerate(valor):
                if cela is None:          # a referencia non opina nesta cela
                    continue
                cela = list(cela) if isinstance(cela, list) else [cela]
                if set(taboa[clave][p]) != set(cela):
                    taboa[clave][p] = cela
                    cambiadas.append(f"{clave}.{PERSOAS[p]}")
        else:
            raise ValueError(f"Clave de referencia descoñecida: {clave}")
    return cambiadas


def engadir_formas(taboa: dict, engadido: dict) -> list[str]:
    """Engade formas a celas sen quitar as que hai: {"celas": {"indicativo.presente.P3": ["cómpre"]}}."""
    feitas = []
    for clave, valor in engadido.get("celas", {}).items():
        base, _, persoa = clave.rpartition(".")
        cela = taboa[base][PERSOAS.index(persoa)] if persoa in PERSOAS else taboa[clave]
        for forma in valor:
            if forma not in cela:
                cela.append(forma)
                feitas.append(clave)
    return feitas


def formas(taboa: dict):
    """Todas as formas dunha táboa como (forma, clave, persoa|None)."""
    for clave, _ in TEMPOS:
        for i, cela in enumerate(taboa[clave]):
            for forma in cela:
                yield forma, clave, PERSOAS[i]
    for clave in FORMAS_NOMINAIS:
        for forma in taboa[clave]:
            yield forma, clave, None


def omitir_encliticos(h):
    """Poda para Hunspell.expand: sen pronomes enclíticos.

    Hunspell xera todas as combinacións teóricas (falándochello...), moitas
    das cales non se usan. Quedamos só coas formas verbais simples: fóra os
    afixos de pronome (pa:) e os que necesitan outro afixo detrás (NEEDAFFIX).
    """
    def omitir(afixo) -> bool:
        return (h.needaffix in afixo.cont) or any(m.startswith("pa:") for m in afixo.morph)
    return omitir


def es_verbo(h, entrada) -> bool:
    """Entrada de verbo que é un lema (non unha raíz alternativa con NEEDAFFIX)."""
    return (any(po.startswith("verbo") for po in entrada.fields("po"))
            and h.needaffix not in entrada.flags)


def unipersoal(taboa: dict) -> bool:
    """Verbos como chover ou amencer: só P3 e P6 no presente."""
    pres = taboa["indicativo.presente"]
    return bool(pres[2]) and not any(pres[p] for p in (0, 1, 3, 4))


def defectivo(taboa: dict) -> bool:
    """Verbos como abolir ou manir: só teñen as formas con desinencia en -i
    (abolimos, abolides), así que faltan o presente P1-P3, P6 e o subxuntivo presente."""
    pres = taboa["indicativo.presente"]
    return (bool(pres[3]) and not any(pres[p] for p in (0, 1, 2, 5))
            and not any(taboa["subxuntivo.presente"]))


def taboas_desde_hunspell(h, lemas: set[str] | None = None, admitir=None) -> dict[str, dict]:
    """Constrúe as táboas de todos os verbos (ou só dos `lemas` indicados).

    `admitir(entrada, lema) -> bool` permite escoller que entradas se usan
    para cada lema (p. ex. só as dunha fonte).
    """
    admitir = admitir or (lambda entrada, lema: True)
    entradas: dict[str, list] = {}
    alomorfos: dict[str, str] = {}   # raíz alternativa -> lema (campo al:)
    for e in h.entries:
        if es_verbo(h, e) and (lemas is None or e.word in lemas) and admitir(e, e.word):
            entradas.setdefault(e.word, []).append((e, False))
            for al in e.fields("al"):
                alomorfos.setdefault(al, e.word)
    for e in h.entries:
        lemas_raiz = set(e.fields("st"))
        if h.needaffix in e.flags and e.word in alomorfos:
            lemas_raiz.add(alomorfos[e.word])
        for st in lemas_raiz:
            if st in entradas and admitir(e, st) and (e, True) not in entradas[st]:
                entradas[st].append((e, True))

    omitir = omitir_encliticos(h)
    taboas = {}
    for lema, lista in entradas.items():
        orixes: dict[tuple, set[bool]] = {}
        for e, alomorfo in lista:
            # As raíces con til (fálar, érer) existen sobre todo para levar
            # enclíticos, e as regras xenéricas fan saír delas formas falsas.
            sospeitosa = alomorfo and ten_acento(e.word) and not ten_acento(lema)
            for f in h.expand(e, omitir):
                for clave, persoa in celas(f.morph):
                    orixes.setdefault((f.form, clave, persoa), set()).add(sospeitosa)
        taboa = taboa_baleira(lema)
        for (forma, clave, persoa), sospeitas in orixes.items():
            if False in sospeitas:
                engadir(taboa, clave, persoa, forma)
        # As formas que só saen de raíces con til úsanse só se a cela quedou
        # baleira: así entra "continúo" (raíz contínuar) pero non "éra".
        for (forma, clave, persoa), sospeitas in orixes.items():
            if False not in sospeitas:
                cela = taboa[clave] if persoa is None else taboa[clave][persoa]
                if not cela or forma in cela:
                    engadir(taboa, clave, persoa, forma)
        reubicar_antepreteritos(taboa)
        taboas[lema] = taboa
    return taboas


_FINS_POSPRETERITO = ("ía", "ías", "ía", "iamos", "iades", "ían")
_FINS_ANTEPRETERITO = ("ra", "ras", "ra", "ramos", "rades", "ran")


def reubicar_antepreteritos(taboa: dict) -> None:
    """Hunspell etiqueta ás veces o antepretérito como pospretérito
    (dixera, bendixera). Móvense as formas que non rematan en -ía."""
    pos, ante = taboa["indicativo.pospreterito"], taboa["indicativo.antepreterito"]
    for p in range(6):
        for forma in list(pos[p]):
            if not forma.endswith(_FINS_POSPRETERITO[p]) and forma.endswith(_FINS_ANTEPRETERITO[p]):
                pos[p].remove(forma)
                if forma not in ante[p]:
                    ante[p].append(forma)


def baleiras(taboa: dict) -> list[str]:
    """Celas sen ningunha forma (o imperativo só ten P2 e P5)."""
    faltan = []
    so_terceiras = unipersoal(taboa)
    for clave, _ in TEMPOS:
        for i, cela in enumerate(taboa[clave]):
            if clave == "imperativo" and (i not in (1, 4) or so_terceiras):
                continue   # a P4 só a ten ir («vamos»); non conta como baleira
            if so_terceiras and i not in (2, 5):
                continue
            if not cela:
                faltan.append(f"{clave}.{PERSOAS[i]}")
    for clave in ("xerundio", "participio"):
        if not taboa[clave]:
            faltan.append(clave)
    return faltan
