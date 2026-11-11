"""Diminutivos en -iño/-iña dos substantivos.

O sufixo é tónico, así que a base perde o til (árbore → arboriña, música → musiquiña).
Nas palabras en -o e -a o diminutivo conserva esa vogal, tamén nos masculinos en -a
(problema → problemiña, atestado no corpus); nas demais leva a do xénero: -iño no
masculino, -iña no feminino (noite → noitiña, home → homiño).

Regras, segundo a terminación do singular:
  - vogal átona -o, -a, -e: cáese (gato → gatiño, casa → casiña, noite → noitiña);
    co cambio gráfico c → qu, g → gu, z → c (barco → barquiño, amigo → amiguiño,
    praza → praciña) e gu → gü cando o u se pronuncia (lingua → lingüiña);
  - -ia, -io, -ie átonos: cáe o ditongo (historia → historiña, espacio → espaciño);
  - se a base queda en vogal, o i do sufixo leva til polo hiato
    (persoa → persoíña, aldea → aldeíña, paseo → paseíño, rúa → ruíña);
  - vogal tónica: -íño/-íña (café → cafeíño, avó → avoíño); os femininos en -á
    (de -án) fan -anciña (irmá → irmanciña);
  - -n e ditongo final: -ciño/-ciña (can → canciño, irmán → irmanciño, nai → naiciña);
  - -r, -l, -s tónico, -z: -iño/-iña (flor → floriña, papel → papeliño,
    país → paisiño, rapaz → rapaciño).

Quedan sen diminutivo os casos nos que a norma non é clara ou a forma sería
estraña: os femininos en -o (foto, moto, radio: sen uso atestado), as que rematan
en ditongo + vogal (raio, maio),
os monosílabos en vogal átona (fe), as palabras graves en -s (lapis, martes),
as rematadas noutras consoantes (álbum, tórax), en -í ou -ú tónicos, as
palabras con guión e as escritas con letras alleas ao galego (curaçao, röntgen).
"""

from __future__ import annotations

VOGAIS = set("aeiouáéíóúü")
LETRAS = set("abcdefghijklmnopqrstuvwxyzñ") | VOGAIS
SEN_TIL = str.maketrans("áéíóú", "aeiou")
# femininos en -á que non veñen de -án: fan -aíña, non -anciña
NON_EN_AN = {"mamá", "fideuá"}


def _ten_vogal(texto: str) -> bool:
    return any(c in VOGAIS for c in texto)


def _vogal_previa(raiz: str) -> bool:
    """A penúltima letra da raíz é vogal pronunciada (o u de qu, gu non o é)."""
    return raiz[-2:-1] in VOGAIS and not raiz[:-1].endswith(("qu", "gu"))


def _base(raiz: str, caida: str) -> str:
    """Axusta a grafía da raíz diante de i: c → qu, g → gu, z → c, gu → gü.
    Se o que cae é o i dun ditongo (espacio, parroquia), a raíz xa ía diante de i."""
    if caida == "i":
        return raiz
    if caida in "ao" and raiz.endswith(("gu", "qu")):     # lingua, quo: o u pronúnciase
        return raiz[:-1] + "ü"
    if raiz.endswith("c"):
        return raiz[:-1] + "qu"
    if raiz.endswith("g"):
        return raiz[:-1] + "gu"
    if raiz.endswith("z"):
        return raiz[:-1] + "c"
    return raiz


def _unir(raiz: str, vogal: str) -> str:
    """raíz (xa sen til) + -iño/-iña, co til do hiato se a raíz remata en vogal."""
    if raiz[-1:] in VOGAIS and raiz[-1] != "ü" and not raiz.endswith(("gu", "qu")):
        return raiz + "íñ" + vogal
    return raiz + "iñ" + vogal


def diminutivo(forma: str, xenero: str) -> str | None:
    """Diminutivo en singular dunha forma singular; xenero 'm' ou 'f'.
    None se non se forma (ver o docstring do módulo)."""
    if len(forma) < 2 or not set(forma) <= LETRAS:
        return None                                       # guións, maiúsculas, curaçao, röntgen
    vogal = "o" if xenero == "m" else "a"
    final = forma[-1]

    # vogal átona final
    if final in "aoe":
        if final == "o" and xenero == "f":
            return None                                   # foto, moto
        if final == "a":
            vogal = "a"                                   # problema → problemiña
        raiz = forma[:-1]
        if not _ten_vogal(raiz):
            return None                                   # fe, pa
        if raiz[-1:] in "iu" and _vogal_previa(raiz):
            return None                                   # raio, maio: ditongo + vogal
        if raiz.endswith("i") and len(raiz) > 1:
            raiz = raiz[:-1]                              # historia, espacio, serie, parroquia
            if not _ten_vogal(raiz):
                return None
            return _unir(_base(raiz.translate(SEN_TIL), "i"), vogal)
        return _unir(_base(raiz.translate(SEN_TIL), final), vogal)

    # vogal tónica final
    if final in "áéó":
        raiz = forma[:-1].translate(SEN_TIL) + final.translate(SEN_TIL)
        if final == "á" and xenero == "f" and forma not in NON_EN_AN:
            return raiz + "nciña"                         # irmá → irmanciña
        return raiz + "íñ" + vogal                        # café → cafeíño

    # ditongo final (pai, nai, rei, boi, grau)
    if final in "iu" and len(forma) > 1 and forma[-2] in "aeo":
        return forma.translate(SEN_TIL) + "ciñ" + vogal

    if final == "n":
        if forma.endswith("ns"):
            return None
        return forma.translate(SEN_TIL) + "ciñ" + vogal  # can → canciño
    if final in "rl":
        return forma.translate(SEN_TIL) + "iñ" + vogal   # flor → floriña
    if final == "z":
        return forma[:-1].translate(SEN_TIL) + "ciñ" + vogal   # rapaz → rapaciño
    if final == "s":
        # só as agudas rematadas en vogal + s: monosílabos (mes) ou co til (país)
        resto = forma[:-1]
        if resto[-1:] not in VOGAIS:
            return None
        nucleos = sum(1 for i, c in enumerate(resto) if c in VOGAIS and (i == 0 or resto[i - 1] not in VOGAIS))
        if resto[-1] not in "áéíóú" and nucleos > 1:
            return None                                   # lapis, martes
        return resto.translate(SEN_TIL) + "siñ" + vogal  # país → paisiño
    return None


def do_lema(formas: dict[str, list[str]]) -> dict[str, list[str]]:
    """Diminutivos dun substantivo a partir das súas formas {ms, fs, mp, fp}.
    Os plurais saen do singular (+s). Os substantivos só en plural
    (tesoiras, anteollos) fórmano desde o singular implícito."""
    saida: dict[str, list[str]] = {}

    def engadir(clave: str, forma: str) -> None:
        lista = saida.setdefault(clave, [])
        if forma not in lista:
            lista.append(forma)

    for x in "mf":
        singulares = formas.get(x + "s", [])
        for f in singulares:
            d = diminutivo(f, x)
            if d:
                engadir(x + "s", d)
                engadir(x + "p", d + "s")
        if not singulares:
            for p in formas.get(x + "p", []):
                if len(p) > 2 and p.endswith("s") and p[-2] in "ao":
                    d = diminutivo(p[:-1], x)
                    if d:
                        engadir(x + "p", d + "s")
    return {k: saida[k] for k in ("ms", "fs", "mp", "fp") if k in saida}


def do_catalogo(rexistros, existentes: set[str]) -> dict[str, dict[str, list[str]]]:
    """id -> diminutivos de cada substantivo, sen as formas que xa son palabras do
    catálogo (cociña non é diminutivo de coza, nin veciño de vezo, nin camiña de
    cama): eses homógrafos teñen a súa propia entrada."""
    saida = {}
    for r in rexistros:
        if r["categoria"] != "substantivo":
            continue
        dims = {}
        for clave, lista in do_lema(r["formas"]).items():
            lista = [f for f in lista if f not in existentes]
            if lista:
                dims[clave] = lista
        if dims:
            saida[r["id"]] = dims
    return saida
