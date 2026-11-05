"""Compara as nosas táboas de conxugación coas do conxugador da RAG.

Dous camiños:

1. Automático (precisa acceso a academia.gal). O conxugador responde a unha
   petición HTTP sinxela; pídense as táboas con calma (1 s entre verbos) e
   gárdanse en fontes/cache/rag/<verbo>.json:

    python3 ferramentas/comparar_rag.py --rag moer reler atraer     # verbos concretos
    python3 ferramentas/comparar_rag.py --rag --todos                # todos os verbos do catálogo
    python3 ferramentas/comparar_rag.py --rag --todos --aceptar      # e garda as táboas como referencia

2. Manual: cópiase a táboa do conxugador tal como se presenta na web nun
   ficheiro docs/rag/<verbo>.txt:

    python3 ferramentas/comparar_rag.py docs/rag/            # informa das diferenzas
    python3 ferramentas/comparar_rag.py --aceptar docs/rag/  # e garda as táboas da RAG
                                                             # en datos/referencia-rag.json

Despois de --aceptar hai que executar importar.py (e capas.py) para que a
referencia se aplique aos datos. O informe de diferenzas escríbese tamén en
docs/rag/diferenzas.tsv.

Formato que se espera (o que sae ao pegar o conxugador):

    Presente        P.Pluscuamperfecto
        provexo         provera
        ...
    Pretérito imperfecto    Futuro
    ...
    Subxuntivo
        Presente
        provexa ...
    Imperativo
        -
        prové
    Infinitivo Conx.
    Xerundio
    Participio
        provido/provisto
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conxugacion as C  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

# Nomes do conxugador da RAG -> claves nosas (indicativo por defecto)
NOMES_RAG = {
    "presente": "indicativo.presente",
    "pretérito imperfecto": "indicativo.copreterito",
    "pretérito perfecto": "indicativo.preterito",
    "p.pluscuamperfecto": "indicativo.antepreterito",
    "pluscuamperfecto": "indicativo.antepreterito",
    "futuro": "indicativo.futuro",
    "condicional": "indicativo.pospreterito",
    "imperativo": "imperativo",
    "infinitivo conx.": "infinitivo.conxugado",
    "infinitivo conxugado": "infinitivo.conxugado",
    "xerundio": "xerundio",
    "participio": "participio",
}
SUBXUNTIVO = {"indicativo.presente": "subxuntivo.presente", "indicativo.copreterito": "subxuntivo.preterito",
              "indicativo.futuro": "subxuntivo.futuro"}
TAMAÑOS = {"xerundio": 1, "participio": 4}


def _nome(texto: str) -> str | None:
    return NOMES_RAG.get(texto.strip().lower().rstrip(":"))


def analizar(texto: str) -> dict:
    """Converte o texto pegado do conxugador nunha táboa coas nosas claves."""
    liñas = [l.strip() for l in texto.splitlines() if l.strip()]
    taboa: dict = {}
    modo_subx = False
    i = 0
    while i < len(liñas):
        partes = [p.strip() for p in re.split(r"\t+|\s{2,}", liñas[i]) if p.strip()]
        if len(partes) == 1 and partes[0].lower() in ("indicativo", "subxuntivo"):
            modo_subx = partes[0].lower() == "subxuntivo"
            i += 1
            continue
        claves = [_nome(p) for p in partes]
        if not claves or any(c is None for c in claves):
            i += 1
            continue
        if modo_subx:
            claves = [SUBXUNTIVO.get(c, c) for c in claves]
        n = max(TAMAÑOS.get(c, 6) for c in claves)
        filas = []
        for j in range(i + 1, min(i + 1 + n, len(liñas))):
            celas = [p.strip() for p in re.split(r"\t+|\s{2,}", liñas[j]) if p.strip()]
            if len(celas) < len(claves) or any(_nome(c) for c in celas):
                break
            filas.append(celas)
        for k, clave in enumerate(claves):
            valores = [f[k] for f in filas]
            if clave in TAMAÑOS:
                formas = [v for v in valores if v != "-"]
                taboa[clave] = [x.strip() for v in formas for x in v.split("/")]
            else:
                taboa[clave] = [[] if v == "-" else [x.strip() for x in v.split("/")] for v in valores]
                taboa[clave] += [[]] * (6 - len(taboa[clave]))
        i += 1 + len(filas)
    if "participio" in taboa and len(taboa["participio"]) == 4:
        # a RAG lista m.sg, f.sg, m.pl, f.pl; nós m.sg, m.pl, f.sg, f.pl
        p = taboa["participio"]
        taboa["participio"] = [p[0], p[2], p[1], p[3]]
    return taboa


# -- conxugador da RAG por HTTP ------------------------------------------------
import html as _html  # noqa: E402
import time  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402

CACHE_RAG = RAIZ / "fontes" / "cache" / "rag"
TIMBRE = re.compile(r"\s*\[[^\]]*\]")
PORTLET = "com_ideit_ragportal_liferay_dictionary_NormalSearchPortlet"
AXENTE = "dicionario-galego (https://github.com/Xocko12/Dicionario-galego)"


def descargar_rag(lema: str, pausa: float = 1.0) -> str | None:
    """HTML do conxugador da RAG para un verbo (da caché se xa está)."""
    CACHE_RAG.mkdir(parents=True, exist_ok=True)
    destino = CACHE_RAG / f"{lema}.json"
    if destino.exists():
        return destino.read_text(encoding="utf-8")
    url = ("https://academia.gal/dicionario?p_p_id=" + PORTLET + "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
           "&p_p_cacheability=cacheLevelPage&_" + PORTLET + "_cmd=cmdConjugateVerb&_" + PORTLET + "_renderMode=load"
           "&_" + PORTLET + "_nounTitle=" + urllib.parse.quote(lema))
    datos = urllib.parse.urlencode({"_" + PORTLET + "_verb": f"/pc/verbos/{lema}.html"}).encode()
    peticion = urllib.request.Request(url, data=datos, headers={
        "User-Agent": AXENTE, "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://academia.gal/dicionario/-/termo/{urllib.parse.quote(lema)}"})
    try:
        with urllib.request.urlopen(peticion, timeout=60) as resposta:
            texto = resposta.read().decode("utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"{lema}: erro ao descargar ({e})")
        return None
    time.sleep(pausa)
    destino.write_text(texto, encoding="utf-8")
    return texto


def analizar_rag_html(texto: str) -> dict:
    """Táboa coas nosas claves a partir da resposta do conxugador (JSON con htmlContent)."""
    try:
        h = json.loads(texto)["htmlContent"]
    except (ValueError, KeyError):
        h = texto
    taboa: dict = {}
    for m in re.finditer(r"<table[^>]*class=\"([^\"]+)\"[^>]*>(.*?)</table>", h, re.S):
        cls, corpo = m.group(1), m.group(2)
        celas = [_html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", corpo, re.S)]
        celas = [c for c in celas if c]
        ths = [_html.unescape(x).strip() for x in re.findall(r"<th[^>]*>(.*?)</th>", corpo, re.S)]
        ths = [t for t in ths if t]

        def cela(v):
            # «toses [ɔ]»: a RAG marca o timbre da vogal tónica; quítase da forma
            v = TIMBRE.sub("", v).strip()
            return [] if v in ("-", "") else [x.strip() for x in v.split("/") if x.strip()]

        if cls == "tabindicativo":
            # 3 bloques de 2 tempos; cada bloque: 6 filas × 2 celas
            claves = [_nome(t) for t in ths]
            for b in range(0, len(claves), 2):
                bloque = celas[b * 6: b * 6 + 12]
                taboa[claves[b]] = [cela(v) for v in bloque[0::2]]
                taboa[claves[b + 1]] = [cela(v) for v in bloque[1::2]]
        elif cls == "tabsubxuntivo":
            claves = [SUBXUNTIVO.get(_nome(t), _nome(t)) for t in ths]
            for i, clave in enumerate(claves):
                taboa[clave] = [cela(v) for v in celas[i * 6: i * 6 + 6]]
        elif cls == "tabimperativo":
            taboa["imperativo"] = [cela(v) for v in celas[:6]]
        elif cls == "tabinfinitivo":
            taboa["infinitivo.conxugado"] = [cela(v) for v in celas[:6]]
        elif cls == "tabxerundio":
            taboa["xerundio"] = [x for v in celas for x in cela(v)]
        elif cls == "tabparticipio":
            p = [cela(v) for v in celas[:4]]
            if len(p) == 4:   # RAG: m.sg, f.sg, m.pl, f.pl -> nós: m.sg, m.pl, f.sg, f.pl
                taboa["participio"] = p[0] + p[2] + p[1] + p[3]
    return taboa if "indicativo.presente" in taboa else {}


def cargar_nosas() -> dict[str, dict]:
    taboas = {}
    for ruta in [RAIZ / "datos" / "conxugacions.jsonl"] + sorted((RAIZ / "datos" / "capas").glob("*.jsonl")):
        for liña in ruta.open(encoding="utf-8"):
            r = json.loads(liña)
            if "taboa" in r:
                taboas.setdefault(r["lema"], r["taboa"])
    return taboas


def comparar(lema: str, rag: dict, nosa: dict) -> list[str]:
    diferenzas = []
    for clave, valor in rag.items():
        if clave in TAMAÑOS:
            if set(valor) != set(nosa.get(clave, [])):
                diferenzas.append(f"{clave}: RAG {valor} / nós {nosa.get(clave)}")
            continue
        for p, cela in enumerate(valor):
            if clave == "imperativo" and p not in (1, 3, 4):
                continue
            nosa_cela = nosa.get(clave, [[]] * 6)[p]
            if set(cela) != set(nosa_cela):
                diferenzas.append(f"{clave}.{C.PERSOAS[p]}: RAG {cela} / nós {nosa_cela}")
    return diferenzas


def main() -> None:
    args = sys.argv[1:]
    aceptar = "--aceptar" in args
    modo_rag = "--rag" in args
    nosas = cargar_nosas()
    if modo_rag:
        lemas = [a for a in args if not a.startswith("--")]
        if "--todos" in args:
            lemas = sorted(nosas)
        fontes = [(lema, "rag") for lema in lemas]
    else:
        rutas = [Path(a) for a in args if not a.startswith("--")]
        fontes = [(f.stem, f) for r in rutas for f in (sorted(r.glob("*.txt")) if r.is_dir() else [r])]
    if not fontes:
        print(__doc__)
        sys.exit(2)
    ref_ruta = RAIZ / "datos" / "referencia-rag.json"
    referencia = json.loads(ref_ruta.read_text(encoding="utf-8")) if ref_ruta.exists() else {
        "_descricion": "Táboas do conxugador da RAG (academia.gal), descargadas con ferramentas/comparar_rag.py "
                       "--rag --aceptar. Mandan sobre as regras de Hunspell-gl e sobre datos/correccions/referencia.json. "
                       "As Normas e o conxugador son normativa gramatical, non o contido do dicionario."}
    total = 0
    aceptados = 0
    sen_rag = []
    informe = (RAIZ / "docs" / "rag" / "diferenzas.tsv").open("a" if modo_rag and "--todos" in args else "w", encoding="utf-8")
    for n, (lema, fonte) in enumerate(fontes, 1):
        if fonte == "rag":
            texto = descargar_rag(lema)
            rag = analizar_rag_html(texto) if texto else {}
        else:
            rag = analizar(fonte.read_text(encoding="utf-8"))
        if not rag:
            sen_rag.append(lema)
            if not modo_rag or len(fontes) < 50:
                print(f"{lema}: sen táboa da RAG")
            continue
        if lema not in nosas:
            print(f"{lema}: non está nas nosas táboas")
            continue
        difs = comparar(lema, rag, nosas[lema])
        total += len(difs)
        if difs or len(fontes) < 50:
            print(f"{lema}: {len(rag)} tempos lidos, {len(difs)} diferenzas")
            for d in difs:
                print("   ", d)
        for d in difs:
            informe.write(f"{lema}\t{d}\n")
        if aceptar:
            referencia[lema] = {"celas": rag}
            aceptados += 1
        if modo_rag and n % 100 == 0:
            print(f"... {n}/{len(fontes)} verbos, {total} diferenzas ata agora", flush=True)
    informe.close()
    if sen_rag:
        print(f"{len(sen_rag)} verbos sen táboa no conxugador da RAG: {', '.join(sen_rag[:30])}")
    if aceptar:
        ref_ruta.write_text(json.dumps(referencia, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"datos/referencia-rag.json actualizado con {aceptados} verbos; executa importar.py e capas.py")
    print(f"total: {len(fontes)} verbos, {total} diferenzas")
    sys.exit(1 if total and not aceptar else 0)


if __name__ == "__main__":
    main()
