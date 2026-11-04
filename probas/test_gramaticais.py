"""Palabras gramaticais: pronomes, artigos e contraccións que teñen que estar
no catálogo coa súa categoría e as súas formas."""

import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

PRONOMES_PERSOAIS = (
    "eu min comigo me ti te che contigo el ela eles elas lle lles se si consigo "
    "o a os as lo la los las no na nos nas nós nosoutros nosoutras connosco "
    "vós vosoutros vosoutras convosco vos vostede vostedes"
).split()

ARTIGOS = "o a os as un unha uns unhas lo la los las".split()

# contracción: (composición, formas)
CONTRACCIONS = {
    "do": (["de", "o"], "do da dos das"),
    "no": (["en", "o"], "no na nos nas"),
    "ao": (["a", "o"], "ao á aos ás"),
    "polo": (["por", "o"], "polo pola polos polas"),
    "co": (["con", "o"], "co coa cos coas"),
    "dun": (["de", "un"], "dun dunha duns dunhas"),
    "nun": (["en", "un"], "nun nunha nuns nunhas"),
    "cun": (["con", "un"], "cun cunha cuns cunhas"),
    "deste": (["de", "este"], "deste desta destes destas"),
    "nese": (["en", "ese"], "nese nesa neses nesas"),
    "daquel": (["de", "aquel"], "daquel daquela daqueles daquelas"),
    "del": (["de", "el"], "del dela deles delas"),
    "disto": (["de", "isto"], "disto"),
    "niso": (["en", "iso"], "niso"),
    "mo": (["me", "o"], "mo ma mos mas"),
    "cho": (["che", "o"], "cho cha chos chas"),
    "llo": (["lle", "o"], "llo lla llos llas"),
    "llelo": (["lles", "o"], "llelo llela llelos llelas"),
    "nolo": (["nos", "o"], "nolo nola nolos nolas"),
    "volo": (["vos", "o"], "volo vola volos volas"),
}

POSESIVOS = {"meu": "meu miña meus miñas", "teu": "teu túa teus túas", "seu": "seu súa seus súas",
             "noso": "noso nosa nosos nosas", "voso": "voso vosa vosos vosas"}
DEMOSTRATIVOS = {"este": "este esta estes estas", "ese": "ese esa eses esas",
                 "aquel": "aquel aquela aqueles aquelas", "isto": "isto", "iso": "iso", "aquilo": "aquilo"}


def cargar():
    lemas = {}
    with (RAIZ / "datos" / "lemas.jsonl").open(encoding="utf-8") as fh:
        for liña in fh:
            r = json.loads(liña)
            lemas[r["id"]] = r
    return lemas


def formas(r):
    return {f for lista in r.get("formas", {}).values() for f in lista} | {r["lema"]}


class ProbasGramaticais(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lemas = cargar()

    def formas_categoria(self, categoria):
        return set().union(*(formas(r) for r in self.lemas.values() if r["categoria"] == categoria))

    def test_pronomes_persoais(self):
        presentes = self.formas_categoria("pronome_persoal")
        self.assertEqual([p for p in PRONOMES_PERSOAIS if p not in presentes], [])

    def test_artigos(self):
        presentes = self.formas_categoria("artigo")
        self.assertEqual([a for a in ARTIGOS if a not in presentes], [])

    def test_contraccions(self):
        for lema, (composicion, esperadas) in CONTRACCIONS.items():
            with self.subTest(lema=lema):
                r = self.lemas[f"{lema}#contracción"]
                self.assertEqual(r["composicion"], composicion)
                self.assertEqual(set(esperadas.split()) - formas(r), set())

    def test_sen_contraccions_duplicadas(self):
        # «da», «coa», «lla» son formas de «do», «co», «llo», non lemas de seu
        for lema in ("da", "das", "dos", "coa", "cos", "lla", "ma", "cha", "na", "pola"):
            self.assertNotIn(f"{lema}#contracción", self.lemas)

    def test_posesivos_e_demostrativos(self):
        for taboa, categoria in ((POSESIVOS, "posesivo"), (DEMOSTRATIVOS, "demostrativo")):
            for lema, esperadas in taboa.items():
                with self.subTest(lema=lema):
                    r = self.lemas[f"{lema}#{categoria}"]
                    self.assertEqual(set(esperadas.split()) - formas(r), set())


if __name__ == "__main__":
    unittest.main()
