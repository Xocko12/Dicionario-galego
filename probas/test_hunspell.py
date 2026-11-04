import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))

from hunspell import Hunspell  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"


class ProbasHunspell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = Hunspell(FIX / "mini.aff", FIX / "mini.dic")

    def formas(self, palabra):
        e = next(e for e in self.h.entries if e.word == palabra)
        return {f.form: " ".join(f.morph) for f in self.h.expand(e)}

    def test_plural_con_condicion(self):
        self.assertEqual(set(self.formas("casa")), {"casa", "casas"})
        self.assertEqual(set(self.formas("mar")), {"mar", "mares"})

    def test_etiquetas_morfoloxicas(self):
        f = self.formas("falar")
        self.assertIn("is:presente P1", f["falo"])

    def test_sufixo_dobre_e_prefixo_cruzado(self):
        f = self.formas("falar")
        self.assertIn("falados", f)          # participio + plural
        self.assertIn("refalo", f)           # prefixo + sufixo
        self.assertIn("refalados", f)

    def test_needaffix(self):
        # a raíz só existe con afixo, e o afixo marcado con NEEDAFFIX tampouco é palabra soa
        self.assertEqual(self.formas("raíz"), {})

    def test_campos(self):
        e = next(e for e in self.h.entries if e.word == "casa")
        self.assertEqual(e.fields("po"), ["substantivo_feminino"])


if __name__ == "__main__":
    unittest.main()
