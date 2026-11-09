"""Importa as capas opcionais (fontes/capas.json) a datos/capas/<capa>.jsonl.

    python3 ferramentas/capas.py [capa ...]

Capas léxicas (digalego, comunidade, terminoloxía): mesmo formato ca
datos/lemas.jsonl, máis o campo "capa"; os verbos levan a táboa de
conxugación dentro ("taboa"). Un lema que xa está no núcleo da RAG, ou nunha
capa anterior, non se repite.

Siglas:      {"forma": "NIF", "tipo": "sigla", "nota": "Número de identificación fiscal", ...}
Onomástica:  {"nome": "Santiago de Compostela", "tipo": "topónimo", ...}
Códigos:     {"codigo": "glg", "tipo": "iso639", "nota": "Galician (639-2/3)"}

Ademais dos módulos de Hunspell-gl, unha capa pode levar "engadidos": ficheiros
propios deste proxecto (fontes/engadidos/<capa>.dic), no mesmo formato, para o
que falta nas fontes (iOS, Google, HDMI, Canberra, Obama...). Levan a fonte "engadidos".

As capas con "importador" non veñen de Hunspell-gl senón doutras fontes de
fontes.json, xa descargadas en fontes/cache/ (descargar.py):
  cidades               GeoNames (cidades do mundo), INE (municipios de España), CAOP (Portugal)
  clubs                 openfootball (clubs de fútbol): só os nomes e as súas variantes
  nomes_outras_linguas  nomes de pía e apelidos correntes (SSA, ONS, Census, Destatis, INSEE, INE-PT, Idescat)
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
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
ENGADIDOS = RAIZ / "fontes" / "engadidos"

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


def engadidos(cfg: dict) -> list[Path]:
    """Ficheiros propios da capa (fontes/engadidos/*.dic), se os hai."""
    return [RAIZ / e for e in cfg.get("engadidos", []) if (RAIZ / e).exists()]


def fonte_de(ruta: Path) -> str:
    if ruta.is_relative_to(ENGADIDOS):
        return "engadidos"
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


# -- capas doutras fontes (fontes/cache/<fonte>/) ------------------------------

def _rexistro(capa: str, nome: str, tipo: str, fonte: str, nota: str = "") -> dict:
    r = {"nome": nome, "tipo": tipo, "capa": capa, "fontes": [fonte]}
    if nota:
        r["nota"] = nota
    return r


def _xuntar(rexistros: list[dict]) -> list[dict]:
    """Un rexistro por (nome, tipo); as fontes súmanse e queda a primeira nota."""
    vistos: dict[tuple, dict] = {}
    for r in rexistros:
        clave = (r["nome"], r["tipo"])
        if clave in vistos:
            for f in r["fontes"]:
                if f not in vistos[clave]["fontes"]:
                    vistos[clave]["fontes"].append(f)
            if "nota" not in vistos[clave] and r.get("nota"):
                vistos[clave]["nota"] = r["nota"]
        else:
            vistos[clave] = r
    return sorted(vistos.values(), key=lambda r: (I.clave_orde(r["nome"]), r["tipo"]))


def _csv(ruta: Path, **kw):
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        yield from csv.reader(fh, **kw)


ARTIGOS_INE = re.compile(r"^(.+), (A|O|As|Os|El|La|Los|Las|Els|Les|Es|Sa|Ses|L'|S')$")


def importar_cidades(capa: str, cfg: dict) -> list[dict]:
    """GeoNames (cidades de máis de 15 000 habitantes), municipios de España (INE) e
    concellos e freguesías de Portugal (CAOP)."""
    saida = []
    for nome, pais, rexion, _ in list(_csv(I.CACHE / "geonames-cidades" / "world-cities.csv"))[1:]:
        # fóra os distritos numerados (Lyon 02, Marseille 13) e os nomes con barras ou parénteses
        if re.search(r"\d$", nome) or any(c in nome for c in "/()"):
            continue
        saida.append(_rexistro(capa, nome.strip(), "topónimo", "geonames-cidades", f"{pais}" + (f" ({rexion})" if rexion else "")))
    for _, _, _, _, nome in list(_csv(I.CACHE / "ine-municipios" / "municipios.csv"))[1:]:
        for variante in nome.split("/"):      # Donostia/San Sebastián
            variante = variante.strip()
            m = ARTIGOS_INE.match(variante)   # «Coruña, A» -> «A Coruña»; «Hospitalet de Llobregat, L'»
            if m:
                variante = m.group(2) + ("" if m.group(2).endswith("'") else " ") + m.group(1)
            saida.append(_rexistro(capa, variante, "topónimo", "ine-municipios", "municipio de España"))
    for _, freguesia, concelho, distrito in list(_csv(I.CACHE / "caop-freguesias" / "freguesias.csv"))[1:]:
        saida.append(_rexistro(capa, concelho.strip(), "topónimo", "caop-freguesias", f"concello de Portugal ({distrito})"))
        saida.append(_rexistro(capa, freguesia.strip(), "topónimo", "caop-freguesias", f"freguesía de {concelho}, Portugal"))
    return _xuntar(saida)


# Palabras dos nomes dos clubs que non identifican o club (siglas de «club de fútbol», xenéricos, partículas).
XENERICOS_CLUBS = {"FC", "CF", "SC", "SD", "UD", "CD", "AD", "RC", "RCD", "CA", "CP", "CE", "UE", "AC", "AS", "SS", "US",
                   "SV", "VfB", "VfL", "VfR", "TSV", "TSG", "FSV", "SpVgg", "SG", "BSC", "FK", "NK", "HNK", "GNK", "KF",
                   "KS", "SK", "ŠK", "MŠK", "PFC", "PFK", "AFC", "BK", "IF", "IFK", "FF", "IK", "GIF", "SF", "SSV", "SSC",
                   "ASD", "SE", "SA", "SAD", "OSC", "RSC", "KV", "KVC", "KAA", "KRC", "KSV", "KSC", "KAS", "KFC", "KVK",
                   "SKN", "SCR", "ASK", "USV", "SVG", "ATSV", "WSG", "LASK", "GAK", "DSV", "ASKÖ", "ESV", "SVK", "VSG",
                   "FCM", "SCU", "USC", "SKU", "TuS", "DJK", "SpVg", "VfV", "SuS", "SVW", "SCB", "Club", "Clube", "Klub",
                   "Real", "Sporting", "Sport", "Sportivo", "Deportivo", "Deportiva", "Desportivo", "Atlético", "Atletico",
                   "Athletic", "Racing", "Union", "Unión", "União", "United", "City", "Town", "County", "Rovers",
                   "Wanderers", "Albion", "Olympique", "Olympic", "Olimpia", "Stade", "Académica", "Académico", "Boavista",
                   "Juventud", "Juventude", "Cultural", "Gimnástica", "Gimnàstic", "Recreativo", "Nacional", "Internacional",
                   "Football", "Fútbol", "Futbol", "Futebol", "Calcio", "Fußball", "Voetbal", "Fotbal", "Fotboll", "Fodbold",
                   "Spor", "Kulübü", "Spartak", "Dynamo", "Dinamo", "Lokomotiv", "Torpedo", "Zenit", "Metalurg", "Shakhtar",
                   "Vorwärts", "Wacker", "Austria", "Young", "Boys", "Old", "First", "New", "North", "South", "East", "West",
                   "Saint", "St.", "St", "San", "Santa", "Santo", "São", "Sant", "Villa", "Ciudad", "Cidade", "Vila", "Mar",
                   "Juniors", "Amateure", "Reserves", "II", "III", "IV", "B", "C", "U21", "U23", "de", "da", "do", "del",
                   "della", "dello", "di", "la", "le", "les", "los", "las", "el", "of", "and", "e", "y", "&", "The", "Los",
                   "Las", "El", "La", "Le", "Les", "A", "O", "Os", "As", "FCB", "RCDE", "RCCV", "Agrupación", "Asociación",
                   "Associação", "Associazione", "Association", "Balompié", "Centre", "Centro", "Ballspielverein",
                   "Ballsportverein", "Betriebssportgemeinschaft", "Breitensport", "Deutsche", "Deutscher", "Armeesportklub",
                   "Sportklub", "Sportverein", "Sportvereinigung", "Sportgemeinschaft", "Sportfreunde", "Spielvereinigung",
                   "Turnverein", "Turn", "Fußballclub", "Fussballclub", "Fußball-Club", "Verein", "Vereniging", "Voetbalvereniging",
                   "Société", "Sociedad", "Sociedade", "Societat", "Società", "Polisportiva", "Unione", "Gruppo", "Grupo",
                   "Esportiu", "Esportiva", "Esportivo", "Esporte", "Esportes", "Clube", "Klubi", "Klubas", "Kluby", "Team",
                   "Maatschappelijke", "Combinatie", "Amateurs", "Católica", "Universidad", "Universidade", "Universitario",
                   "Universitatea", "Universitario", "Independiente", "Estudiantes", "Central", "Nacional", "Municipal",
                   "Provincial", "Regional", "Académie", "Academy", "Juvenil", "Juventus", "Jeunesse", "Étoile", "Espérance",
                   "Avenir", "Progrès", "Renaissance", "Stella", "Virtus", "Pro", "Alemannia", "Germania", "Borussia", "Fortuna",
                   "Victoria", "Viktoria", "Concordia", "Preußen", "Hertha"}


def importar_clubs(capa: str, cfg: dict) -> list[dict]:
    """Clubs de fútbol dos ficheiros de openfootball. De cada club gárdase o nome, cada
    variante e cada palabra distintiva como rexistros dunha soa palabra (Bayern, Dortmund,
    Celta), que son os que usa o teclado; os datos de estadios, cidades e anos non se len."""
    saida = []
    for ruta in sorted((I.CACHE / "openfootball-clubs").glob("*.txt")):
        pais = ruta.stem.split("_")[1].replace("-", " ").title().replace(" N ", " e ")
        club = None
        for raw in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
            texto = raw.split("#", 1)[0].rstrip()
            if not texto.strip() or texto.lstrip().startswith("="):
                continue
            if texto.lstrip().startswith("|"):
                if club is None:
                    continue
                # fóra as variantes noutras linguas («Bayern Munich [en]», «Teneriffa [de]»)
                variantes = [v.strip() for v in texto.split("|") if v.strip() and not re.search(r"\[[a-z]{2}\]", v)]
            elif re.match(r"^\s*(i+|[a-z])\)\s", texto):   # «ii) Real Madrid B»: filiais
                club = None
                continue
            elif not texto[0].isspace():
                nome = re.sub(r"\s*\([^)]*\)\s*$", "", texto.split(",", 1)[0]).strip()   # «Wimbledon FC (1889-2004)»
                if not nome or nome[0].isdigit() and " " not in nome:
                    club = None
                    continue
                club = nome
                saida.append(_rexistro(capa, nome, "club", "openfootball-clubs", f"fútbol, {pais}"))
                variantes = [nome]
            else:
                continue
            palabras = set()
            for v in variantes:
                v = re.sub(r"\s*\([^)]*\)\s*$", "", v).strip()
                if not v:
                    continue
                if " " not in v and "." not in v and (len(v) >= 4 or v.isupper()):
                    palabras.add(v)
                for p in v.replace("/", " ").split():
                    if p.endswith("."):      # abreviaturas: «Atl. Madrid», «Dep. La Coruña»
                        continue
                    p = p.strip(",")
                    if p in XENERICOS_CLUBS or (len(p) < 4 and not p.isupper()) or not p[0].isupper() \
                            or not p.replace("-", "").replace("'", "").replace("’", "").isalpha():
                        continue
                    palabras.add(p)
            for p in sorted(palabras):
                if p != club:
                    saida.append(_rexistro(capa, p, "club", "openfootball-clubs", f"{club} (fútbol, {pais})"))
    return _xuntar(saida)


def _capitalizar(nome: str) -> str:
    """De maiúsculas a inicial maiúscula: JEAN-PIERRE -> Jean-Pierre, O'BRIEN -> O'Brien, MCCARTHY -> McCarthy."""
    partes = []
    for parte in re.split(r"([-' ])", nome):
        if len(parte) <= 1 or parte in "-' ":
            partes.append(parte)
            continue
        p = parte[0].upper() + parte[1:].lower()
        if p.startswith("Mc") and len(p) > 3:
            p = "Mc" + p[2].upper() + p[3:]
        partes.append(p)
    return "".join(partes)


def _nome_simple(nome: str) -> bool:
    return bool(nome) and " " not in nome and nome.replace("-", "").replace("'", "").isalpha() and len(nome) > 1


def importar_nomes_outras_linguas(capa: str, cfg: dict) -> list[dict]:
    """Nomes de pía e apelidos correntes noutras linguas, dunha soa palabra, coa frecuencia
    mínima que fai que sexan de uso corrente e non rarezas. Un rexistro por (nome, tipo),
    coas linguas en que é corrente na nota: «apelido: inglés, alemán»."""
    acumulado: dict[tuple[str, str], dict] = {}
    dg = I.CACHE / "damegender"

    def engadir(nome: str, tipo: str, lingua: str, fonte: str):
        nome = nome.strip()
        if nome.isupper():
            nome = _capitalizar(nome)
        if not _nome_simple(nome):
            return
        r = acumulado.setdefault((nome, tipo), {"linguas": [], "fontes": []})
        if lingua not in r["linguas"]:
            r["linguas"].append(lingua)
        if fonte not in r["fontes"]:
            r["fontes"].append(fonte)

    def ficheiro(nome_ficheiro: str, tipo: str, lingua: str, minimo: int):
        for fila in _csv(dg / nome_ficheiro):
            if len(fila) < 2 or not fila[1].strip().replace(".", "").isdigit():
                continue
            if int(float(fila[1])) >= minimo:
                engadir(fila[0], tipo, lingua, "damegender")

    # inglés: nomes de pía da SSA (1880-2008), apelidos do Reino Unido (ONS) e dos EUA (Census 2010)
    for fila in list(_csv(I.CACHE / "ssa-nomes" / "baby-names.csv"))[1:]:
        engadir(fila[1], "antropónimo", "inglés", "ssa-nomes")
    ficheiro("gbsurnames.csv", "apelido", "inglés", 3)
    ficheiro("ussurnames.csv", "apelido", "inglés", 5000)
    # alemán (Destatis): nomes de pía en maiúsculas sen tremas (os que os levan engádense a man)
    ficheiro("deall.csv", "antropónimo", "alemán", 5)
    ficheiro("desurnames.csv", "apelido", "alemán", 3)
    # francés (INSEE): só apelidos (os nomes de pía veñen sen acentos e engádense a man)
    ficheiro("frsurnames.csv", "apelido", "francés", 3)
    # portugués (INE)
    ficheiro("ptall.csv", "antropónimo", "portugués", 1)
    ficheiro("ptsurnames.csv", "apelido", "portugués", 1)
    # catalán (Idescat 2022): «JÚLIA/JULIA», «ZOE VALENTINA»
    for fila in _csv(dg / "nomscatalunya.csv"):
        if len(fila) >= 4 and fila[0].isdigit():
            for nome in fila[2].split("/"):
                engadir(nome, "antropónimo", "catalán", "damegender")
    descricion = {"antropónimo": "nome de pía", "apelido": "apelido"}
    saida = []
    for (nome, tipo), r in acumulado.items():
        s = _rexistro(capa, nome, tipo, r["fontes"][0], f"{descricion[tipo]}: {', '.join(r['linguas'])}")
        s["fontes"] = r["fontes"]
        saida.append(s)
    return _xuntar(saida)


IMPORTADORES = {"cidades": importar_cidades, "clubs": importar_clubs, "nomes_outras_linguas": importar_nomes_outras_linguas}


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

    # as de «script» van á parte; as de «importador» léñense doutras fontes (abaixo)
    importadas = {capa: cfg for capa, cfg in config.items() if "importador" in cfg}
    config = {capa: cfg for capa, cfg in config.items() if "modulos" in cfg}
    for capa, cfg in importadas.items():
        if capa in pedidas:
            rexistros = IMPORTADORES[cfg["importador"]](capa, cfg)
            escribir(capa, _xuntar(rexistros + importar_onomastica(capa, engadidos(cfg))))
    pedidas = [c for c in pedidas if c in config]
    rutas_capa = {capa: [r for m in cfg["modulos"] for r in ficheiros(m)] + engadidos(cfg)
                  for capa, cfg in config.items()}
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
