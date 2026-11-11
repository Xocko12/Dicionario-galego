"""Diminutivos en -iño/-iña dos substantivos e adxectivos (ferramentas/diminutivos.py e datos/lemas.jsonl)."""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))

import diminutivos as D  # noqa: E402

# (forma, xénero) -> diminutivo; None = sen diminutivo
REFERENCIA = {
    # vogal átona final
    ("gato", "m"): "gatiño", ("gata", "f"): "gatiña", ("casa", "f"): "casiña",
    ("noite", "f"): "noitiña", ("home", "m"): "homiño", ("coche", "m"): "cochiño",
    ("ano", "m"): "aniño", ("cuarto", "m"): "cuartiño",
    # cambios gráficos
    ("barco", "m"): "barquiño", ("bico", "m"): "biquiño", ("amigo", "m"): "amiguiño",
    ("praza", "f"): "praciña", ("mozo", "m"): "mociño", ("lingua", "f"): "lingüiña",
    ("auga", "f"): "auguiña", ("sangue", "m"): "sanguiño", ("parque", "m"): "parquiño",
    # ditongo átono final
    ("historia", "f"): "historiña", ("espacio", "m"): "espaciño", ("serie", "f"): "seriña",
    ("parroquia", "f"): "parroquiña",
    # hiato: o i do sufixo leva til
    ("persoa", "f"): "persoíña", ("aldea", "f"): "aldeíña", ("paseo", "m"): "paseíño",
    ("rúa", "f"): "ruíña", ("lúa", "f"): "luíña", ("avoa", "f"): "avoíña",
    # a base perde o til
    ("árbore", "f"): "arboriña", ("música", "f"): "musiquiña", ("lámpada", "f"): "lampadiña",
    # vogal tónica final
    ("café", "m"): "cafeíño", ("avó", "m"): "avoíño", ("sofá", "m"): "sofaíño",
    ("irmá", "f"): "irmanciña", ("mamá", "f"): "mamaíña",
    # -n e ditongo
    ("can", "m"): "canciño", ("irmán", "m"): "irmanciño", ("corazón", "m"): "corazonciño",
    ("nai", "f"): "naiciña", ("pai", "m"): "paiciño",
    # -r, -l, -z, -s tónico
    ("flor", "f"): "floriña", ("muller", "f"): "mulleriña", ("papel", "m"): "papeliño",
    ("animal", "m"): "animaliño", ("rapaz", "m"): "rapaciño", ("luz", "f"): "luciña",
    ("país", "m"): "paisiño", ("mes", "m"): "mesiño",
    # monosílabos: vogal tónica (boíño está no corpus)
    ("bo", "m"): "boíño", ("boa", "f"): "boíña", ("fe", "f"): "feíña",
    # adxectivos
    ("pequeno", "m"): "pequeniño", ("rico", "m"): "riquiño", ("guapa", "f"): "guapiña",
    ("quente", "f"): "quentiña", ("feliz", "m"): "feliciño", ("azul", "f"): "azuliña",
    ("tranquilo", "m"): "tranquiliño",
    # masculinos en -a: conservan o -a (problemiña está no corpus)
    ("problema", "m"): "problemiña", ("artista", "m"): "artistiña",
    # sen diminutivo
    ("foto", "f"): None, ("lapis", "m"): None, ("martes", "m"): None, ("raio", "m"): None,
    ("álbum", "m"): None, ("garda-roupa", "m"): None, ("röntgen", "m"): None,
}


class ProbasRegras(unittest.TestCase):
    def test_referencia(self):
        for (forma, xenero), esperado in REFERENCIA.items():
            with self.subTest(forma=forma):
                self.assertEqual(D.diminutivo(forma, xenero), esperado)

    def test_do_lema(self):
        self.assertEqual(D.do_lema({"ms": ["gato"], "fs": ["gata"], "mp": ["gatos"], "fp": ["gatas"]}),
                         {"ms": ["gatiño"], "fs": ["gatiña"], "mp": ["gatiños"], "fp": ["gatiñas"]})
        self.assertEqual(D.do_lema({"fp": ["tesoiras"]}), {"fp": ["tesoiriñas"]})   # só plural
        self.assertEqual(D.do_lema({"ms": ["rapaz"], "fs": ["rapaz", "rapaza"]})["fs"], ["rapaciña"])
        # adxectivos invariables: os dous xéneros
        self.assertEqual(D.do_lema({"ms": ["pobre"], "mp": ["pobres"]}, ambos_xeneros=True),
                         {"ms": ["pobriño"], "mp": ["pobriños"], "fs": ["pobriña"], "fp": ["pobriñas"]})
        self.assertEqual(D.do_lema({"ms": ["socialista"], "mp": ["socialistas"]}, ambos_xeneros=True),
                         {"ms": ["socialistiña"], "mp": ["socialistiñas"]})
        # feminino en -á: -anciña só se o masculino é en -án
        self.assertEqual(D.do_lema({"ms": ["irmán"], "fs": ["irmá"]})["fs"], ["irmanciña"])
        self.assertEqual(D.do_lema({"ms": ["chan"], "fs": ["chá"]})["fs"], ["chanciña"])
        self.assertEqual(D.do_lema({"ms": ["mao"], "fs": ["má"]}), {"ms": ["maíño"], "mp": ["maíños"],
                                                                   "fs": ["maíña"], "fp": ["maíñas"]})

    def test_homografos_fora(self):
        # cociña non é diminutivo de coza: xa é outra palabra do catálogo
        dims = D.do_catalogo([{"id": "coza#substantivo", "categoria": "substantivo",
                               "formas": {"fs": ["coza"], "fp": ["cozas"]}}], {"cociña", "cociñas"})
        self.assertEqual(dims, {})


class ProbasDatos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lemas = {}
        with (RAIZ / "datos" / "lemas.jsonl").open(encoding="utf-8") as fh:
            for liña in fh:
                r = json.loads(liña)
                cls.lemas[r["id"]] = r

    def test_catalogo(self):
        casos = {
            "gato#substantivo": {"ms": ["gatiño"], "fs": ["gatiña"], "mp": ["gatiños"], "fp": ["gatiñas"]},
            "casa#substantivo": {"fs": ["casiña"], "fp": ["casiñas"]},
            "irmán#substantivo": {"ms": ["irmanciño"], "fs": ["irmanciña"],
                                  "mp": ["irmanciños"], "fp": ["irmanciñas"]},
            "can#substantivo": {"ms": ["canciño"], "mp": ["canciños"]},
            "nube#substantivo": {"fs": ["nubiña"], "fp": ["nubiñas"]},
            "rico#adxectivo": {"ms": ["riquiño"], "fs": ["riquiña"], "mp": ["riquiños"], "fp": ["riquiñas"]},
            "quente#adxectivo": {"ms": ["quentiño"], "mp": ["quentiños"], "fs": ["quentiña"], "fp": ["quentiñas"]},
            "bo#adxectivo": {"ms": ["boíño"], "fs": ["boíña"], "mp": ["boíños"], "fp": ["boíñas"]},
        }
        for ident, esperado in casos.items():
            with self.subTest(ident=ident):
                self.assertEqual(self.lemas[ident].get("diminutivos"), esperado)

    def test_homografos(self):
        # palabras con entrada propia non se dan como diminutivo doutra
        # (noitiña e carriño son lemas da RAG; cociña non vén de coza, nin golfiño de golfo)
        for ident in ("coza#substantivo", "vezo#substantivo", "cama#substantivo", "golfo#substantivo",
                      "noite#substantivo", "carro#substantivo"):
            with self.subTest(ident=ident):
                self.assertNotIn("diminutivos", self.lemas.get(ident, {}))

    def test_so_substantivos_e_adxectivos(self):
        for r in self.lemas.values():
            if "diminutivos" in r:
                self.assertIn(r["categoria"], ("substantivo", "adxectivo"), r["id"])

    def test_lexicalizados(self):
        # pequeniño é lema da RAG: pequeno non o repite como diminutivo
        self.assertIn("pequeniño#adxectivo", self.lemas)
        self.assertNotIn("pequeniño", self.lemas["pequeno#adxectivo"].get("diminutivos", {}).get("ms", []))


if __name__ == "__main__":
    unittest.main()
