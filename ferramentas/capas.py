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
  apertium              léxico (substantivos, adxectivos, adverbios) do monolingüe de Apertium, cos seus paradigmas
  wiktionary            léxico da capa definicions-gl (Wiktionary galego), coa flexión regular (flexionar)

E as capas con "derivado" (vocabularios): o seu módulo .dic xérase en fontes/cache/derivados/
a partir doutras fontes (os vocabularios en PDF, con pypdf) e lese como un módulo máis.
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
    if ruta.is_relative_to(I.CACHE / "derivados"):
        return {"vocabularios": "vocabularios-galegos"}.get(ruta.stem, ruta.stem)
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


def _sen_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


# Exónimos ingleses que o dicionario inglés non recolle como tales e GeoNames usa como nome principal.
EXONIMOS_INGLESES = {"Prague", "Warsaw", "Krakow", "Cracow", "Bucharest", "Belgrade", "Kiev", "Athens", "Rome", "Milan",
                     "Naples", "Florence", "Venice", "Turin", "Genoa", "Geneva", "Zurich", "Basel", "Lucerne", "Munich",
                     "Cologne", "Nuremberg", "Hanover", "Brussels", "Antwerp", "Bruges", "Ghent", "The Hague", "Copenhagen",
                     "Gothenburg", "Lisbon", "Seville", "Saragossa", "Corunna", "Moscow", "Saint Petersburg", "Cairo",
                     "Alexandria", "Damascus", "Beirut", "Jerusalem", "Mecca", "Medina", "Baghdad", "Tehran", "Beijing",
                     "Nanjing", "Canton", "Tokyo", "Kyoto", "Seoul", "Bangkok", "Rangoon", "Bombay", "Calcutta", "Madras",
                     "Havana", "Mexico City", "Bogota", "Panama City", "Casablanca", "Marrakesh", "Tangier", "Algiers",
                     "Tunis", "Tripoli", "Khartoum", "Addis Ababa", "Mogadishu", "Cape Town", "Luanda", "Kinshasa",
                     "Brazzaville", "Riyadh", "Jeddah", "Muscat", "Sanaa", "Yerevan", "Tashkent", "Ashgabat", "Ulaanbaatar",
                     "Kathmandu", "Dhaka", "Jakarta", "Phnom Penh", "Vientiane", "Kuala Lumpur", "Singapore", "Taipei",
                     "Pyongyang", "Lhasa", "Macau", "Quebec", "Montreal", "Asuncion", "Brasilia", "Belem", "Oporto",
                     "Luxembourg", "Monaco", "Nice", "Toulouse", "Bordeaux", "Strasbourg", "Lille", "Rheims", "Dunkirk",
                     "Lausanne", "Berne", "Hamburg", "Dresden", "Leipzig", "Frankfurt", "Stuttgart", "Dusseldorf",
                     "Aachen", "Mainz", "Trier", "Freiburg", "Heidelberg", "Salzburg", "Innsbruck", "Graz", "Ljubljana",
                     "Zagreb", "Sarajevo", "Skopje", "Tirana", "Sofia", "Chisinau", "Minsk", "Vilnius", "Riga", "Tallinn",
                     "Helsinki", "Stockholm", "Oslo", "Reykjavik", "Rotterdam", "Amsterdam", "Utrecht", "Gdansk", "Wroclaw",
                     "Poznan", "Lodz", "Szczecin", "Lublin", "Brno", "Bratislava", "Kosice", "Budapest", "Cluj", "Timisoara",
                     "Iasi", "Constanta", "Plovdiv", "Thessaloniki", "Patras", "Heraklion", "Nicosia", "Istanbul", "Ankara",
                     "Izmir", "Smyrna", "Antalya", "Bursa", "Trebizond", "Odessa", "Kharkiv", "Lviv", "Sevastopol",
                     "Kaliningrad", "Volgograd", "Kazan", "Samara", "Nizhny Novgorod", "Yekaterinburg", "Novosibirsk",
                     "Vladivostok", "Irkutsk", "Mumbai", "Kolkata", "Chennai", "Delhi", "New Delhi", "Lahore", "Karachi",
                     "Kabul", "Tbilisi", "Baku", "Bishkek", "Dushanbe", "Almaty", "Astana", "Colombo", "Hanoi", "Saigon",
                     "Manila", "Shanghai", "Tianjin", "Chongqing", "Wuhan", "Shenzhen", "Guangzhou", "Hong Kong", "Osaka",
                     "Nagoya", "Yokohama", "Sapporo", "Busan", "Incheon", "Ottawa", "Toronto", "Vancouver", "Lima", "Quito",
                     "Caracas", "Montevideo", "Santiago", "Salvador", "Recife", "Fortaleza", "Manaus", "Curitiba",
                     "Sao Paulo", "Rio de Janeiro", "Buenos Aires", "Cordoba", "Rosario", "Mendoza", "Valparaiso", "Medellin",
                     "Cali", "Cartagena", "Guayaquil", "La Paz", "Sucre", "Santa Cruz", "Tegucigalpa", "Managua",
                     "San Salvador", "Guatemala City", "Kingston", "Port-au-Prince", "Santo Domingo", "San Juan",
                     "Nassau", "Nairobi", "Kampala", "Kigali", "Dar es Salaam", "Dodoma", "Lusaka", "Harare", "Maputo",
                     "Antananarivo", "Windhoek", "Gaborone", "Pretoria", "Johannesburg", "Durban", "Lagos", "Abuja",
                     "Accra", "Dakar", "Bamako", "Niamey", "Ouagadougou", "Abidjan", "Yamoussoukro", "Conakry", "Freetown",
                     "Monrovia", "Lome", "Cotonou", "Porto-Novo", "Yaounde", "Douala", "Libreville", "Malabo", "Bangui",
                     "N'Djamena", "Asmara", "Djibouti", "Juba", "Benghazi", "Rabat", "Fez", "Fes", "Oran", "Constantine",
                     "Sfax", "Sousse", "Nouakchott", "Bissau", "Praia", "Mogadiscio", "Bombay"}


def importar_cidades(capa: str, cfg: dict) -> list[dict]:
    """GeoNames (cidades de máis de 15 000 habitantes), municipios de España (INE) e
    concellos e freguesías de Portugal (CAOP).

    GeoNames dá en inglés os nomes das cidades famosas (Vienna, Munich, Lisbon), que xa
    teñen nome galego na capa toponimos (Viena, Múnic, Lisboa): quedan fóra os nomes que
    son palabras do dicionario inglés e non están en toponimos, e os que só se distinguen
    dun topónimo galego polos acentos (Berlin/Berlín, Paris/París). Nos países de fala
    inglesa non se aplica o filtro do dicionario: alí eses son os nomes (Leeds, Yonkers)."""
    # nos países de fala inglesa os nomes do dicionario inglés son os nomes das cidades (Leeds, Yonkers)
    paises_ingles = {"United Kingdom", "Ireland", "United States", "Canada", "Australia", "New Zealand", "South Africa",
                     "Jamaica", "Trinidad and Tobago", "Barbados", "Bahamas", "Belize", "Guyana", "Malta", "Nigeria",
                     "Ghana", "Kenya", "Uganda", "Zambia", "Zimbabwe", "Liberia", "Sierra Leone", "Gibraltar", "Bermuda"}
    toponimos = {json.loads(l)["nome"] for l in (SAIDA / "toponimos.jsonl").open(encoding="utf-8")}
    toponimos_sen_acentos = {_sen_acentos(t) for t in toponimos}
    ingles = set()
    for liña in (I.CACHE / "libreoffice-en" / "en_GB.dic").read_text(encoding="utf-8", errors="replace").splitlines():
        palabra = liña.split("/", 1)[0].strip()
        if palabra[:1].isupper():
            ingles.add(palabra)
    saida = []
    for nome, pais, rexion, _ in list(_csv(I.CACHE / "geonames-cidades" / "world-cities.csv"))[1:]:
        nome = nome.strip()
        # fóra os distritos numerados (Lyon 02, Marseille 13) e os nomes con barras ou parénteses
        if re.search(r"\d$", nome) or any(c in nome for c in "/()"):
            continue
        exonimo = (nome in ingles or nome in EXONIMOS_INGLESES) and pais not in paises_ingles
        if nome not in toponimos and (exonimo or _sen_acentos(nome) in toponimos_sen_acentos):
            continue
        saida.append(_rexistro(capa, nome, "topónimo", "geonames-cidades", f"{pais}" + (f" ({rexion})" if rexion else "")))
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


# -- capas léxicas doutras fontes (Apertium, Wiktionary) --------------------------

VOGAIS = "aeiouáéíóúü"


def _silabas_aprox(palabra: str) -> int:
    return len(re.findall(r"[aeiouáéíóúü]+", palabra))


def _plural(lema: str) -> str | None:
    """Plural regular segundo as regras de Hunspell-gl (SFX 10 e 12) e as Normas; None se é invariable."""
    if lema.endswith("l"):
        # polisílabas agudas: animal/animais, papel/papeis, fusil/fusís; graves (fácil, túnel) e monosílabas (sol): -es
        acento_non_final = re.search(r"[áéíóú]", lema[:-1]) and not re.search(r"[áéíóú][^aeiouáéíóú]*$", lema)
        if _silabas_aprox(lema) > 1 and not acento_non_final:
            return lema[:-2] + "ís" if lema.endswith("il") else lema[:-1] + "is"
        return lema + "es"
    if lema.endswith("r"):
        return lema + "es"
    if lema.endswith("z"):
        return lema[:-1] + "ces"
    if lema.endswith("x"):
        return None
    if lema.endswith("s"):
        if re.search(r"[aeiou]ís$", lema):          # país/países (hiato: queda o til)
            return lema + "es"
        if re.search(r"[áéíóú]s$", lema):          # compás/compases, francés/franceses, anís/anises
            sen_til = lema[:-2] + "áéíóú aeiou".split()[1]["áéíóú".index(lema[-2])]
            return sen_til + "ses"
        return lema + "es" if _silabas_aprox(lema) == 1 else None   # gas/gases; lapis, martes invariables
    if lema.endswith("h"):
        return lema + ("es" if lema.endswith("sh") else "s")
    return lema + "s"


def _feminino(lema: str) -> str | None:
    """Feminino dun adxectivo (ou substantivo con moción de xénero) segundo SFX 14/15/16 de Hunspell-gl."""
    for fin, sub in (("o", "a"), ("án", "á"), ("ón", "ona"), ("és", "esa"), ("ín", "ina"), ("ún", "úa")):
        if lema.endswith(fin):
            return lema[: -len(fin)] + sub
    if lema.endswith("or"):
        return lema + "a"
    return None


def flexionar(lema: str, categoria: str, xenero: str | None) -> dict[str, list[str]]:
    """Formas (ms, fs, mp, fp) dun lema sen paradigma propio, coas regras regulares."""
    plural = _plural(lema)
    if categoria == "adxectivo":
        fem = _feminino(lema)
        formas = {"ms": [lema]}
        if fem:
            formas["fs"] = [fem]
        if plural:
            formas["mp"] = [plural]
        if fem:
            formas["fp"] = [_plural(fem) or fem]
        return formas
    if categoria == "substantivo":
        if xenero == "feminino":
            return {"fs": [lema], **({"fp": [plural]} if plural else {})}
        return {"ms": [lema], **({"mp": [plural]} if plural else {})}
    return {"ms": [lema]}   # adverbios, como no núcleo


def _grafias_erradas() -> set[str]:
    """Palabras que os ficheiros .rep de Hunspell-gl marcan como erradas («^estructura$ estrutura»)."""
    erradas = set()
    for ruta in (SRC / "comunidade" / "suxestións").glob("*.rep"):
        for liña in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\^([^\s$]+)\$\s", liña)
            if m:
                erradas.add(m.group(1))
    return erradas


LEMA_VALIDO = re.compile(r"^[a-záéíóúñü]+(-[a-záéíóúñü]+)*$")


def _rexistro_lexico(capa, lema, categoria, formas, xenero, fonte, frecuencias):
    r = {"id": f"{lema}#{categoria}", "lema": lema, "categoria": categoria, "capa": capa}
    if xenero:
        r["xenero"] = xenero
    if formas:
        r["formas"] = formas
    todas = {lema} | {f for lista in formas.values() for f in lista}
    r["frecuencia"] = sum(frecuencias.get(f, 0) for f in todas)
    r["fontes"] = [fonte]
    return r


def importar_apertium(capa: str, cfg: dict, xa_vistos: set[str], frecuencias: dict) -> list[dict]:
    """Substantivos, adxectivos e adverbios do monolingüe de Apertium que non están nas capas
    anteriores, coas formas que dan os seus paradigmas (sen superlativos nin nomes propios)."""
    import xml.etree.ElementTree as ET
    root = ET.parse(I.CACHE / "apertium-glg" / "apertium-glg.glg.dix").getroot()

    def entradas(el):
        saida = []
        for e in el.findall("e"):
            texto, tags, pars = "", [], []
            for ch in e:
                if ch.tag == "i":
                    texto += "".join(ch.itertext())
                elif ch.tag == "p":
                    l, r = ch.find("l"), ch.find("r")
                    texto += "".join(l.itertext()) if l is not None else ""
                    if r is not None:
                        tags += [s.get("n") for s in r.findall("s")]
                elif ch.tag == "par":
                    pars.append(ch.get("n"))
            saida.append((texto, tags, pars))
        return saida

    pardefs = {pd.get("n"): entradas(pd) for pd in root.iter("pardef")}

    def expandir(texto, tags, pars):
        if not pars:
            return [(texto, tags)]
        saida = []
        for ptexto, ptags, ppars in pardefs[pars[0]]:
            for t, tg in expandir(texto + ptexto, tags + ptags, ppars):
                saida += expandir(t, tg, pars[1:])
        return saida

    erradas = _grafias_erradas()
    categorias = {"n": "substantivo", "adj": "adxectivo", "adv": "adverbio"}
    rexistros = {}
    for sec in root.findall("section"):
        for texto, tags, pars in entradas(sec):
            pass
        for e in sec.findall("e"):
            lema = e.get("lm")
            if not lema or not LEMA_VALIDO.match(lema) or lema in erradas:
                continue
            texto, pars = "", []
            for ch in e:
                if ch.tag == "i":
                    texto += "".join(ch.itertext())
                elif ch.tag == "p":
                    l = ch.find("l")
                    texto += "".join(l.itertext()) if l is not None else ""
                elif ch.tag == "par":
                    pars.append(ch.get("n"))
            formas_tags = expandir(texto, [], pars)
            if not formas_tags or not formas_tags[0][1]:
                continue
            cat = categorias.get(formas_tags[0][1][0])
            if not cat:
                continue
            ident = f"{lema}#{cat}"
            if ident in xa_vistos or ident in rexistros:
                continue
            formas: dict[str, list[str]] = {}
            xeneros = set()
            for forma, tg in formas_tags:
                if "sup" in tg or "acr" in tg or not LEMA_VALIDO.match(forma):
                    continue
                xen = "m" if "m" in tg else "f" if "f" in tg else "mf"
                num = "sg" if "sg" in tg else "pl" if "pl" in tg else "sp"
                claves = [(g, n) for g in (("m", "f") if xen == "mf" else (xen,)) for n in (("sg", "pl") if num == "sp" else (num,))]
                for g, n in claves:
                    xeneros.add(g)
                    clave = g + ("s" if n == "sg" else "p")
                    if forma not in formas.setdefault(clave, []):
                        formas[clave].append(forma)
            if cat == "substantivo" and xeneros == {"m", "f"} and formas.get("ms") == formas.get("fs"):
                formas = {k: v for k, v in formas.items() if k[0] == "m"}   # estudante: común aos dous xéneros
                xenero = None
            elif cat == "substantivo":
                xenero = {"m": "masculino", "f": "feminino"}.get(next(iter(xeneros), ""), None) if len(xeneros) == 1 else None
            else:
                xenero = None
            if cat == "adverbio":
                formas = {"ms": [lema]}
            elif lema not in formas.get("ms", []) + formas.get("fs", []):
                continue   # paradigma mal aplicado na fonte: «edificatorioo», «vehementeo»
            if any(len(re.findall(r"[áéíóú]", f)) > 1 for lista in formas.values() for f in lista + [lema]):
                continue   # dous tiles: «picónón», «acuátís» (erros da fonte)
            rexistros[ident] = _rexistro_lexico(capa, lema, cat, formas, xenero, "apertium-glg", frecuencias)
    xa_vistos.update(rexistros)
    return sorted(rexistros.values(), key=lambda r: (I.clave_orde(r["lema"]), r["id"]))


def importar_wiktionary(capa: str, cfg: dict, xa_vistos: set[str], frecuencias: dict) -> list[dict]:
    """Substantivos, adxectivos e adverbios da capa definicions-gl (Wiktionary galego) que non están
    nas capas anteriores, coa flexión regular; fóra as entradas que son grafías alternativas doutras."""
    erradas = _grafias_erradas()
    rexistros = {}
    ruta = SAIDA / "definicions-gl.jsonl"
    if not ruta.exists():
        return []
    for liña in ruta.open(encoding="utf-8"):
        r = json.loads(liña)
        lema, cat = r["lema"], r["categoria"]
        if cat not in ("substantivo", "adxectivo", "adverbio") or not LEMA_VALIDO.match(lema) or lema in erradas:
            continue
        ident = f"{lema}#{cat}"
        if ident in xa_vistos or ident in rexistros:
            continue
        definicions = [a["definicion"].strip().lower() for a in r["acepcions"]]
        # entradas que só remiten a outra: grafías alternativas e formas flexionadas (feminino de, plural de)
        remite = r"^\(?[^)]*\)?\s*(grafía|variante|forma alternativa|forma non normativa|sinónimo de|feminino|forma feminina|plural|forma plural|participio|mariñeira, feminino)"
        if all(re.match(remite, d) for d in definicions):
            continue
        xenero = r.get("xenero") if cat == "substantivo" else None
        formas = flexionar(lema, cat, xenero)
        rexistros[ident] = _rexistro_lexico(capa, lema, cat, formas, xenero, "wiktionary-gl", frecuencias)
    xa_vistos.update(rexistros)
    return sorted(rexistros.values(), key=lambda r: (I.clave_orde(r["lema"]), r["id"]))


# -- capa derivada: termos dos vocabularios en PDF ----------------------------------

DERIVADOS_DIR = I.CACHE / "derivados"
PAL = r"[a-záéíóúñüç][a-záéíóúñüç'·-]*"
CATEGORIAS_VOC = {"f": ("substantivo", "feminino"), "m": ("substantivo", "masculino"), "s.f.": ("substantivo", "feminino"),
                  "s.m.": ("substantivo", "masculino"), "s.": ("substantivo", None), "adx.": ("adxectivo", None),
                  "v.": ("verbo", None), "v.t.": ("verbo", None), "v.i.": ("verbo", None), "v.p.": ("verbo", None),
                  "v.tr.": ("verbo", None), "v.intr.": ("verbo", None), "adv.": ("adverbio", None),
                  "s.eadx.": ("substantivo", None), "s.m.ef.": ("substantivo", None), "n": ("substantivo", None),
                  "nm": ("substantivo", "masculino"), "nf": ("substantivo", "feminino"), "adj": ("adxectivo", None)}


def _categoria_voc(texto: str | None):
    if not texto:
        return None
    c = re.sub(r"\s+", "", texto.lower()).strip("()").replace("s.f", "s.f.").replace("s.m", "s.m.").replace("..", ".")
    return CATEGORIAS_VOC.get(c) or CATEGORIAS_VOC.get(c + ".") or CATEGORIAS_VOC.get(c.rstrip("."))


def _termos_vocabulario(nome: str, texto: str):
    """(termo, (categoria, xenero) | None) de cada entrada dun vocabulario, segundo a súa maqueta."""
    saida = []

    def eng(t, cat):
        t = re.sub(r"\s*\([^)]*\)", "", t.strip().strip(".,;:")).strip().lower()
        for v in re.split(r"[,;/]| ou ", t):
            v = v.strip()
            c = cat
            if v.endswith("/a"):
                v, c = v[:-2], cat or ("adxectivo", None)
            if re.fullmatch(PAL, v) and len(v) >= 3:
                saida.append((v, c))

    if nome.startswith(("usc-", "uvigo-viceversa")):            # «22 acordo marco europeo m»
        for m in re.finditer(r"^\s*\d{1,4}\.?\s+(.+?)\s+\(?(f pl|m pl|f|m|v|adx|adv)\)?\s*$", texto, re.M):
            eng(m.group(1), _categoria_voc(m.group(2)))
    elif nome in ("udc-dereito", "udc-deportes"):               # «Adopción s. f. adopción»
        for m in re.finditer(r"^(.+?) (s\. ?[fm]\.|s\. e adx\.|s\. m\. e f\.|adx\.|v\. ?[tip]\.(?: e p\.)?|adv\.) (.+?)\.?\s*$", texto, re.M):
            eng(m.group(3), _categoria_voc(m.group(2)))
    elif nome in ("udc-matematica", "udc-fisica-quimica"):      # «Apotema: apotema»
        for m in re.finditer(r"^([A-ZÁÉÍÓÚ][^:\n]*?):\s*\S", texto, re.M):
            eng(m.group(1), None)
    elif nome.startswith("lexicool"):                            # «Previsión: s.f. previsión»
        for m in re.finditer(r"^([A-ZÁÉÍÓÚ][^:\n]*?):\s*(s\.[fm]\.)?", texto, re.M):
            eng(m.group(1), _categoria_voc(m.group(2)))
    elif nome.startswith("udc-"):                                # «Antropometría antropometría s.f.»
        for m in re.finditer(r"^(\S+) (\S+) (s\. ?[fm]\.|adx\.|v\.(?: tr\.| intr\.)?|adv\.|[fm]\.)\s*$", texto, re.M):
            eng(m.group(2), _categoria_voc(m.group(3)) or _categoria_voc("s." + m.group(3)))
    elif nome == "uvigo-xuridico-administrativo":                # «12. acordo (D01) s. m.»
        for m in re.finditer(r"^\d+\.\s+(.+?)\s+\([A-Z0-9, ]+\)\s+(s\. ?[fm]\.|adx\.|v\. ?[tip]\.|adv\.)", texto, re.M):
            eng(m.group(1), _categoria_voc(m.group(2)))
    elif nome.startswith(("cirp-", "rag-")):                     # «polgada s.f. Medida de...»; «gl sinónimo»
        for m in re.finditer(r"^(" + PAL + r"(?: " + PAL + r"){0,3})\s?(loc\.)?(s\.[fm]\.|s\.|adx\.|v\.[tip]\.|v\.|adv\.)(?=\s|[A-ZÁÉÍÓÚ])", texto, re.M):
            if not m.group(2):
                eng(m.group(1), _categoria_voc(m.group(3)))
        for m in re.finditer(r"^gl\s+(" + PAL + r")\s*$", texto, re.M):
            eng(m.group(1), None)
    elif nome.startswith("realiter-"):                           # «glg aborto euxénesico (s.m.)»
        for m in re.finditer(r"^\s*glg?\s+(.+?)\s*(\((?:s|n)\.?\s?[mf]\.?\)|n [mf]|adj\.?|v\.?)?\s*$", texto, re.M):
            eng(m.group(1), _categoria_voc(m.group(2)))
    return saida


def _categoria_inferida(lema: str):
    """Categoría e xénero dun termo sen marca, polo final da palabra."""
    if lema.endswith(("ar", "er", "ir")) and not lema.endswith(("ular", "olar", "ilar", "énder")):
        return "verbo", None
    if lema.endswith(("ico", "ivo", "oso", "ábel", "able", "íbel", "ible", "ario", "ante", "ente", "ístico", "al", "ar", "il")) and not lema.endswith(("mento", "dade")):
        return "adxectivo", None
    if lema.endswith(("ción", "sión", "dade", "axe", "ez", "eza", "ía", "ura", "ncia", "ite", "ose", "ase", "emia", "tude", "ice", "ie", "se", "a")):
        return "substantivo", "feminino"
    return "substantivo", "masculino"


def _flags_nominal(lema: str, cat: str, mocion: bool = False) -> str:
    """Flags de Hunspell-gl polos finais, como fai o módulo da RAG (10 plural, 12 plural en -l, 14/15/16 feminino)."""
    polisilaba_aguda_l = lema.endswith("l") and len(re.findall(r"[aeiouáéíóú]+", lema)) > 1 and not re.search(r"[áéíóú]", lema[:-2])
    if cat == "adxectivo":
        if lema.endswith("o"):
            return "10,15"
        if lema.endswith("or"):
            return "10,14"
        if lema.endswith(("án", "és", "ín")):
            return "10,15"
        if lema.endswith("ón"):
            return "10,16"
        if lema.endswith("l"):
            return "12" if polisilaba_aguda_l else "10"
        return "" if lema.endswith(("s", "x")) else "10"
    if lema.endswith("l"):
        return "12" if polisilaba_aguda_l else "10"
    if lema.endswith(("s", "x")):
        return "10" if len(re.findall(r"[aeiouáéíóú]+", lema)) == 1 else ""
    if mocion:
        return "10,15" if lema.endswith("o") else "10,14" if lema.endswith("or") else "10"
    return "10"


_MODELOS_VERBOS: dict[str, tuple] = {}


def _modelos_verbos() -> dict[str, tuple]:
    """Verbos do módulo da RAG con al: (raíz acentuada) e segunda liña: {verbo: (flags, al, raíz, flags2)}."""
    if _MODELOS_VERBOS:
        return _MODELOS_VERBOS
    liñas = [l.split("#")[0].strip() for l in (SRC / "rag" / "gl" / "correcto.dic").read_text(encoding="utf-8").splitlines()]
    segunda = {}
    for l in liñas:
        m = re.match(r"^(\S+?)/(\S+) st:(\S+)$", l)
        if m:
            segunda[m.group(3)] = (m.group(1), m.group(2))
    for l in liñas:
        m = re.match(r"^([a-záéíóúñü]+)/([\d,]+) po:verbo.* al:(\S+)$", l)
        if m and m.group(1) in segunda:
            _MODELOS_VERBOS[m.group(1)] = (m.group(2), m.group(3), *segunda[m.group(1)])
    return _MODELOS_VERBOS


# Compostos dos verbos irregulares (transpoñer, sobrevir, predicir): non se conxugan por modelo.
IRREGULARES = ("pór", "poñer", "ter", "vir", "dicir", "facer", "traer", "saír", "oír", "caer", "crer", "parir", "durmir",
               "subir", "fuxir", "servir", "seguir", "sentir", "mentir", "pedir", "construír", "estar", "haber", "poder",
               "querer", "saber", "caber", "valer", "pracer", "ver", "ler", "rir", "ir", "dar", "ser")
PREFIXOS = ("re", "des", "pre", "con", "com", "sub", "sobre", "inter", "trans", "en", "em", "pro", "de", "per", "ante",
            "contra", "entre", "ex", "in", "im", "super", "auto", "co", "a", "ad", "ob", "sus", "dis", "retro", "pos", "post")


def _composto_irregular(verbo: str) -> bool:
    for x in IRREGULARES:
        if verbo != x and verbo.endswith(x) and verbo[: -len(x)] in PREFIXOS + tuple(p1 + p2 for p1 in PREFIXOS for p2 in PREFIXOS):
            return True
    return False


def liñas_verbo_modelo(verbo: str, tipo: str = "transitiva") -> list[str] | None:
    """As dúas liñas de Hunspell-gl dun verbo regular novo, copiando os flags e a posición do acento
    do verbo da RAG co final máis longo en común (polo menos 4 letras): consensuar como suar.
    Os compostos dos irregulares (transpoñer) quedan fóra: teñen a súa táboa en referencia.json."""
    if _composto_irregular(verbo):
        return None
    modelos = _modelos_verbos()
    mellor = None
    for v in modelos:
        n = 0
        while n < min(len(v), len(verbo)) and v[-1 - n] == verbo[-1 - n]:
            n += 1
        if n >= 4 and (mellor is None or n > mellor[0]):
            mellor = (n, v)
    if not mellor:
        return None
    flags, al, _, flags2 = modelos[mellor[1]]
    pos = next((i for i, c in enumerate(reversed(al)) if c in "áéíóú"), None)
    if pos is None or pos >= len(verbo):
        return None
    acentuada = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}.get(verbo[-1 - pos])
    if not acentuada:
        return None
    al_novo = verbo[:-1 - pos] + acentuada + verbo[len(verbo) - pos:]
    return [f"{verbo}/{flags} po:verbo ts:{tipo} al:{al_novo}  # como {mellor[1]}", f"{al_novo}/{flags2} st:{verbo}"]


# Primeiros elementos de compostos cultos: con eles non se parte a palabra ao buscar anacos pegados.
PREFIXOS_COMPOSICION = {"electro", "micro", "macro", "hiper", "hipo", "auto", "termo", "foto", "radio", "bio", "xeo", "neuro",
                        "cardio", "hidro", "tele", "video", "vídeo", "aero", "nano", "mono", "poli", "multi", "semi", "super",
                        "inter", "intra", "extra", "ultra", "anti", "contra", "sobre", "ciber", "agro", "psico", "socio", "fisio",
                        "quimio", "crono", "cripto", "homo", "hetero", "proto", "pseudo", "pseudo", "endo", "ecto", "hemi",
                        "tetra", "penta", "hexa", "hepta", "octo", "quilo", "mili", "centi", "deci", "mega", "giga", "xiga",
                        "audio", "áudio", "magneto", "piezo", "turbo", "servo", "ferro", "cloro", "fluor", "sulfo", "nitro",
                        "hidroxi", "metil", "etil", "fenil", "benzo", "ciclo", "oxi", "dinamo", "estereo", "espectro", "osteo",
                        "artro", "dermato", "gastro", "hemato", "hepato", "nefro", "onco", "oftalmo", "oto", "pneumo", "uro",
                        "xineco", "mamo", "angio", "arterio", "bronco", "cito", "histo", "inmuno", "linfo", "mielo", "miocardio",
                        "nasal", "odonto", "patolo", "psiquiatr", "reumato", "trombo", "vaso", "ventrículo", "electrón", "gravi",
                        "calor", "vapor", "metal", "mineral", "cristal", "parasit", "fungi", "ovo", "espermato", "placa", "placo"}


def derivar_vocabularios(capa: str, cfg: dict) -> Path | None:
    """fontes/cache/derivados/vocabularios.dic: os termos dunha palabra dos vocabularios en PDF
    (fontes/cache/vocabularios-galegos/), no formato de Hunspell-gl, para lelo como un módulo máis.
    Só os termos: as definicións non se copian. Quedan fóra os que xa están no núcleo ou nas capas
    anteriores (calquera categoría), as grafías erradas segundo Hunspell-gl, as que só se
    distinguen dunha palabra coñecida polos tiles (saida/saída) e os anacos pegados."""
    # pypdf cambia a extracción se fontTools está instalado (e nalgúns PDF sae lixo): sempre sen el,
    # para que o resultado sexa o mesmo en calquera máquina
    sys.modules.setdefault("fontTools", None)
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"capa {capa}: omitida (precisa pypdf; pip install -r requirements.txt)")
        return None
    cartafol = I.CACHE / "vocabularios-galegos"
    if not cartafol.exists():
        print(f"capa {capa}: omitida (sen fontes/cache/vocabularios-galegos; descargar.py)")
        return None
    import logging
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    termos: dict[str, dict] = {}
    for ruta in sorted(cartafol.glob("*.pdf")):
        try:
            texto = "\n".join((p.extract_text() or "") for p in PdfReader(ruta).pages)
        except Exception as e:   # noqa: BLE001
            print(f"capa {capa}: non se le {ruta.name}: {e}")
            continue
        for termo, cat in _termos_vocabulario(ruta.stem, texto):
            r = termos.setdefault(termo, {"cats": [], "fontes": []})
            if cat and cat not in r["cats"]:
                r["cats"].append(cat)
            if ruta.stem not in r["fontes"]:
                r["fontes"].append(ruta.stem)
    # o que xa coñecemos, con calquera categoría; e as súas formas sen tiles, para cazar «saida»
    coñecidos, sen_tiles = set(), set()
    for ruta in [I.DATOS / "lemas.jsonl"] + [SAIDA / f"{c}.jsonl" for c in ("digalego", "comunidade", "terminoloxia")]:
        if ruta.exists():
            for l in ruta.open(encoding="utf-8"):
                r = json.loads(l)
                formas = {r["lema"]} | {f for lista in r.get("formas", {}).values() for f in lista}
                coñecidos.update(formas)
                sen_tiles.update(_sen_acentos(f) for f in formas)
    erradas = _grafias_erradas()
    # nomes propios e siglas (en minúsculas): nos vocabularios bilingües aparecen como termos (madrid, vigo, garcía, ascii)
    propios = set()
    for ruta in [I.DATOS / "nomes.jsonl"] + [SAIDA / f"{c}.jsonl" for c in ("toponimos", "antroponimos", "organizacions", "clubs", "cidades", "siglas")]:
        if ruta.exists():
            for l in ruta.open(encoding="utf-8"):
                r = json.loads(l)
                nome = r.get("nome") or r.get("forma") or ""
                if " " not in nome:
                    propios.add(nome.lower())
    liñas = ["# Termos dos vocabularios en PDF (fontes/cache/vocabularios-galegos/), xerado por capas.py. Só termos, sen definicións."]
    n = 0
    for termo in sorted(termos, key=I.clave_orde):
        r = termos[termo]
        if termo in coñecidos or termo in erradas or termo in propios or len(termo) > 24 or "·" in termo:
            continue
        if len(re.findall(r"[áéíóú]", termo)) > 1:
            continue   # dous tiles: anacos pegados polo PDF (satélitemeteorolóxico)
        if len(termo) >= 11 and any(termo[:i] in coñecidos and termo[i:] in coñecidos and termo[:i] not in PREFIXOS_COMPOSICION
                                    for i in range(6, len(termo) - 4)):
            continue   # dúas palabras coñecidas pegadas (dispositivomonolítico), non compostos (electrocinético)
        if _sen_acentos(termo) in sen_tiles:
            continue   # só difire polos tiles dunha palabra coñecida (saida/saída)
        cats = r["cats"] or [_categoria_inferida(termo)]
        for cat, xenero in cats:
            if cat == "verbo":
                if termo.endswith(("ar", "er", "ir")):
                    v = liñas_verbo_modelo(termo)
                    if v:
                        liñas += v
                        n += 1
            elif cat == "adverbio":
                liñas.append(f"{termo} po:adverbio")
                n += 1
            elif cat == "adxectivo":
                liñas.append(f"{termo}/{_flags_nominal(termo, 'adxectivo')} po:adxectivo".replace("/ po:", " po:"))
                n += 1
            else:
                po = f"substantivo_{xenero}" if xenero else "substantivo"
                fl = _flags_nominal(termo, "substantivo")
                liñas.append(f"{termo}{'/' + fl if fl else ''} po:{po}")
                n += 1
    DERIVADOS_DIR.mkdir(parents=True, exist_ok=True)
    saida = DERIVADOS_DIR / f"{capa}.dic"
    saida.write_text("\n".join(liñas) + "\n", encoding="utf-8")
    print(f"fontes/cache/derivados/{capa}.dic: {n} entradas de {len(termos)} termos dunha palabra")
    return saida


DERIVADOS = {"vocabularios": derivar_vocabularios}


IMPORTADORES_LEXICOS = {"apertium": importar_apertium, "wiktionary": importar_wiktionary}


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
    todas_pedidas = set(pedidas)
    for capa, cfg in importadas.items():
        if capa in pedidas and cfg["tipo"] != "lexico":
            rexistros = IMPORTADORES[cfg["importador"]](capa, cfg)
            escribir(capa, _xuntar(rexistros + importar_onomastica(capa, engadidos(cfg))))
    pedidas = [c for c in pedidas if c in config]
    rutas_capa = {capa: [r for m in cfg["modulos"] for r in ficheiros(m)] + engadidos(cfg)
                  for capa, cfg in config.items()}
    for capa, cfg in config.items():   # módulos derivados doutras fontes (PDF), xerados agora
        if "derivado" in cfg:
            ruta = DERIVADOS[cfg["derivado"]](capa, cfg)
            if ruta:
                rutas_capa[capa] = [ruta] + rutas_capa[capa]
            else:
                config = {c: k for c, k in config.items() if c != capa}
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
    for capa, cfg in importadas.items():   # léxicas doutras fontes, despois das de Hunspell-gl
        if cfg["tipo"] == "lexico":
            rexistros = IMPORTADORES_LEXICOS[cfg["importador"]](capa, cfg, xa_vistos, frecuencias)
            if capa in todas_pedidas:
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
