"""Lector mínimo de dicionarios Hunspell (.aff/.dic).

Expande cada entrada do dicionario coas súas regras de afixos e devolve
as formas xeradas xunto coas etiquetas morfolóxicas (po:, is:, st:...).

Só implementa o que usa o dicionario galego de Proxecto Trasno:
FLAG num, SFX/PFX con condicións, sufixos dobres (flags de continuación),
produto cruzado prefixo+sufixo e NEEDAFFIX. Non trata palabras compostas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Affix:
    kind: str            # "SFX" ou "PFX"
    flag: str
    cross: bool
    strip: str
    add: str
    cont: tuple[str, ...]
    cond: re.Pattern
    morph: tuple[str, ...]

    def applies(self, word: str) -> bool:
        if self.kind == "SFX":
            return word.endswith(self.strip) and bool(self.cond.search(word))
        return word.startswith(self.strip) and bool(self.cond.match(word))

    def apply(self, word: str) -> str:
        if self.kind == "SFX":
            base = word[: len(word) - len(self.strip)] if self.strip else word
            return base + self.add
        return self.add + word[len(self.strip):]


@dataclass
class Entry:
    word: str
    flags: tuple[str, ...]
    morph: tuple[str, ...]
    source: str = ""     # ficheiro .dic de onde vén a entrada

    def fields(self, key: str) -> list[str]:
        """Valores dun campo morfolóxico, p. ex. fields("po") -> ["verbo"]."""
        prefix = key + ":"
        return [m[len(prefix):] for m in self.morph if m.startswith(prefix)]


@dataclass
class Form:
    form: str
    entry: Entry
    morph: tuple[str, ...]   # etiquetas engadidas polos afixos aplicados
    affixes: tuple[str, ...] = field(default=())  # flags aplicados, por orde


def _parse_flags(text: str, mode: str) -> tuple[str, ...]:
    if not text:
        return ()
    if mode == "num":
        return tuple(f for f in text.split(",") if f)
    if mode == "long":
        return tuple(text[i:i + 2] for i in range(0, len(text), 2))
    return tuple(text)


def _cond_regex(kind: str, cond: str) -> re.Pattern:
    if cond == ".":
        return re.compile("")
    # As condicións de Hunspell xa son clases de caracteres compatibles con regex.
    return re.compile(cond + "$") if kind == "SFX" else re.compile("^" + cond)


class Hunspell:
    def __init__(self, aff_path: str | Path, dic_paths: str | Path | list):
        self.flag_mode = "char"
        self.needaffix: str | None = None
        self.forbidden: str | None = None
        self.onlyincompound: str | None = None
        self.affixes: dict[str, list[Affix]] = {}
        self.entries: list[Entry] = []
        self._load_aff(Path(aff_path))
        if isinstance(dic_paths, (str, Path)):
            dic_paths = [dic_paths]
        for dic in dic_paths:
            self._load_dic(Path(dic))

    # -- lectura -----------------------------------------------------------
    def _load_aff(self, path: Path) -> None:
        headers: dict[str, tuple[str, bool]] = {}
        with path.open(encoding="utf-8") as fh:
            for raw in fh:
                line = raw.split("#", 1)[0].strip()
                if not line:
                    continue
                parts = line.split()
                key = parts[0]
                if key == "FLAG":
                    self.flag_mode = parts[1]
                elif key == "NEEDAFFIX":
                    self.needaffix = parts[1]
                elif key == "FORBIDDENWORD":
                    self.forbidden = parts[1]
                elif key == "ONLYINCOMPOUND":
                    self.onlyincompound = parts[1]
                elif key in ("SFX", "PFX"):
                    flag = parts[1]
                    if flag not in headers and len(parts) == 4 and parts[3].isdigit():
                        headers[flag] = (key, parts[2] == "Y")
                        self.affixes.setdefault(flag, [])
                        continue
                    _, cross = headers[flag]
                    strip = "" if parts[2] == "0" else parts[2]
                    add, _, cont = parts[3].partition("/")
                    add = "" if add == "0" else add
                    cond = parts[4] if len(parts) > 4 else "."
                    self.affixes[flag].append(Affix(
                        kind=key, flag=flag, cross=cross, strip=strip, add=add,
                        cont=_parse_flags(cont, self.flag_mode),
                        cond=_cond_regex(key, cond),
                        morph=tuple(parts[5:]),
                    ))

    def _load_dic(self, path: Path) -> None:
        """Le un .dic. Acepta tamén os módulos fonte de Proxecto Trasno,
        sen número de entradas na primeira liña e con comentarios (#)."""
        with path.open(encoding="utf-8") as fh:
            for n, raw in enumerate(fh):
                line = raw.split("#", 1)[0].strip()
                if not line or (n == 0 and line.isdigit()):
                    continue
                head, *morph = re.split(r"[ \t]+", line)
                word, _, flags = head.partition("/")
                self.entries.append(Entry(word, _parse_flags(flags, self.flag_mode), tuple(morph), str(path)))

    # -- expansión ---------------------------------------------------------
    def _affixes_for(self, flags, kind):
        for flag in flags:
            for affix in self.affixes.get(flag, ()):
                if affix.kind == kind:
                    yield affix

    def expand(self, entry: Entry, skip=None) -> list[Form]:
        """Todas as formas válidas que xera unha entrada.

        `skip(affix) -> bool` permite podar ramas (p. ex. os pronomes
        enclíticos, que multiplican as formas por centos).
        """
        out: list[Form] = []
        keep = (lambda a: not skip(a)) if skip else (lambda a: True)
        flags = entry.flags
        if self.onlyincompound and self.onlyincompound in flags:
            return out
        if self.forbidden and self.forbidden in flags:
            return out
        if not (self.needaffix and self.needaffix in flags):
            out.append(Form(entry.word, entry, ()))

        def needs_more(affix: Affix) -> bool:
            return bool(self.needaffix and self.needaffix in affix.cont)

        suffixed: list[tuple[str, Affix, Affix | None]] = []
        for sfx in self._affixes_for(flags, "SFX"):
            if not keep(sfx) or not sfx.applies(entry.word):
                continue
            w1 = sfx.apply(entry.word)
            suffixed.append((w1, sfx, None))
            # sufixo dobre: o primeiro sufixo trae flags de continuación
            for sfx2 in self._affixes_for(sfx.cont, "SFX"):
                if keep(sfx2) and sfx2.applies(w1):
                    suffixed.append((sfx2.apply(w1), sfx2, sfx))

        for word, last, first in suffixed:
            if needs_more(last):
                continue
            chain = (first.flag, last.flag) if first else (last.flag,)
            morph = (first.morph if first else ()) + last.morph
            out.append(Form(word, entry, morph, chain))

        for pfx in self._affixes_for(flags, "PFX"):
            if not keep(pfx) or not pfx.applies(entry.word):
                continue
            if not needs_more(pfx):
                out.append(Form(pfx.apply(entry.word), entry, pfx.morph, (pfx.flag,)))
            if not pfx.cross:
                continue
            for word, last, first in suffixed:
                if not last.cross or (first and not first.cross):
                    continue
                if pfx.applies(word):
                    chain = (pfx.flag,) + ((first.flag,) if first else ()) + (last.flag,)
                    morph = pfx.morph + (first.morph if first else ()) + last.morph
                    out.append(Form(pfx.apply(word), entry, morph, chain))
        return out
