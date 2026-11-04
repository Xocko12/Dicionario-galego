"""Xeración sistemática de formas con enclíticos. Precisa fontes/cache/
(ferramentas/descargar.py); se non está, sáltase."""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))

import conxugacion as C  # noqa: E402
import encliticos  # noqa: E402

CACHE = RAIZ / "fontes" / "cache" / "hunspell-gl" / "gl.aff"


@unittest.skipUnless(CACHE.exists(), "precisa fontes/cache/")
class ProbasSistematicas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importar as I
        from hunspell import Hunspell
        mods = I.modulos()
        fonte_de = {str(r): (f, e) for f, e, r in mods}
        h = Hunspell(I.HUNSPELL / "gl.aff", [r for _, _, r in mods])
        taboas = {}
        simples = set()
        for liña in (RAIZ / "datos" / "conxugacions.jsonl").open(encoding="utf-8"):
            v = json.loads(liña)
            taboas[v["lema"]] = v["taboa"]
            simples.update(f for f, _, _ in C.formas(v["taboa"]))
        lemas = ["dicir", "dar", "ser", "ir", "haber", "chover", "erguer"]
        saida = encliticos.sistematicas(h, lemas, lambda e, l: fonte_de[e.source][0] == "drag", taboas, simples)
        cls.formas = {}
        for r in saida:
            cls.formas.setdefault(r["forma"], []).append((r["lema"], tuple(r["pronomes"])))

    def test_contraccions_completas(self):
        for forma in ("díxomo", "díxoma", "díxomos", "díxomas", "díxocho", "díxollo", "díxonolo",
                      "díxovolo", "díxollelo", "dámo", "dareicho", "dixéronmo", "díxoselle"):
            with self.subTest(forma=forma):
                self.assertIn(forma, self.formas)

    def test_alomorfos_e_tiles(self):
        self.assertIn(("dicir", ("o",)), self.formas["dicilo"])     # -r + o -> -lo
        self.assertIn(("dar", ("o",)), self.formas["dámolo"])       # -s + o -> -lo, co til
        self.assertIn(("ser", ("o",)), self.formas["éo"])
        self.assertIn(("erguer", ("te",)), self.formas["érguete"])

    def test_sen_formas_mal_formadas(self):
        for forma in ("érádela", "háánllelo", "íríate", "dicírmelo", "falándochello"):
            self.assertNotIn(forma, self.formas)
        for forma in self.formas:
            self.assertTrue(encliticos.ben_formada(forma), forma)

    def test_unipersoais_fora(self):
        self.assertFalse(any(l == "chover" for lista in self.formas.values() for l, _ in lista))


if __name__ == "__main__":
    unittest.main()
