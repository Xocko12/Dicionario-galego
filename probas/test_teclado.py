"""Lista de palabras do teclado (construir.formas_teclado): sen variantes con maiúsculas das
palabras comúns, cos nomes propios e siglas útiles e sen lixo."""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))
import construir  # noqa: E402


class ProbasTeclado(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lemas, conx, frec, nomes, encl = construir.cargar()
        capas = construir.cargar_capas()
        cls.formas = construir.formas_teclado(lemas, conx, frec, nomes, encl, capas)

    def test_sen_maiusculas_das_palabras_comuns(self):
        # Ao deslizar, «ISO»/«Iso» (sigla, cidade), «SE» (sueste), «Como» (cidade), «Paz» (nome) ou «A»
        # (ampere) saían no canto de «iso», «se», «como», «paz» e «a»: só entra a palabra común.
        for comun, propio in (("iso", "ISO"), ("iso", "Iso"), ("se", "SE"), ("como", "Como"), ("paz", "Paz"),
                              ("a", "A"), ("o", "O"), ("de", "De"), ("en", "EN"), ("eu", "EU"), ("mar", "Mar"),
                              ("xa", "XA"), ("fe", "Fe"), ("celta", "CELTA")):
            with self.subTest(propio=propio):
                self.assertTrue(comun in self.formas, comun)
                self.assertTrue(propio not in self.formas, propio)

    def test_excepcions_revisadas(self):
        # datos/correccions/teclado.json: o nome manda sobre a palabra común rara, que queda con 0
        for nome, comun in (("Londres", "londres"), ("Luís", "luís"), ("Brasil", "brasil"), ("Xunta", "xunta")):
            with self.subTest(nome=nome):
                self.assertGreater(self.formas[nome], 0)
                self.assertEqual(self.formas[comun], 0)

    def test_sen_empates_entre_maiusculas_e_minusculas(self):
        # cando conviven dúas grafías dunha palabra, a frecuencia decide sen empate
        por_minusculas = {}
        for f, n in self.formas.items():
            por_minusculas.setdefault(f.lower(), []).append(n)
        empates = [k for k, ns in por_minusculas.items() if len(ns) > 1 and sorted(ns)[-1] == sorted(ns)[-2]]
        self.assertEqual(empates, [])

    def test_nomes_propios_e_siglas(self):
        for n in ("iOS", "iPhone", "iPad", "Android", "WhatsApp", "Google", "Apple", "Microsoft", "Netflix",
                  "HDMI", "5G", "Bizum", "Londres", "Madrid", "Lisboa", "Berlín", "Canberra", "York",
                  "Compostela", "Galicia", "Vigo", "Ourense", "Einstein", "Castelao", "Rosalía", "Obama",
                  "Dépor", "ONU", "NIF", "Xoán", "Uxía",
                  # cidades, municipios e freguesías; clubs; nomes doutras linguas
                  "Mumbai", "Alcobendas", "Gaia", "Hospitalet", "Bayern", "Dortmund", "Arenteiro", "Lakers",
                  "John", "Lennon", "McCartney", "Jon", "Ander", "Pol", "Juan", "Müller", "Jürgen", "Etxeberria",
                  "Qashqai", "Levi's", "Nutella", "Lacoste"):
            with self.subTest(nome=n):
                self.assertTrue(n in self.formas, n)
        # «Obradoiro» (o club) ou «Golf» (o coche) son palabras comúns (obradoiro, golf): só entra a minúscula
        self.assertTrue("obradoiro" in self.formas and "Obradoiro" not in self.formas)
        # «Camiño» ou «Ordes» son tamén palabras comúns (camiño, orde): só entra a minúscula
        self.assertTrue("camiño" in self.formas and "Camiño" not in self.formas)
        self.assertTrue("ordes" in self.formas and "Ordes" not in self.formas)
        # os nomes só coa grafía das fontes; as variantes dun mesmo nome, unha soa
        self.assertNotIn("Iphone", self.formas)
        self.assertTrue({"YouTube", "Youtube"} & set(self.formas))
        self.assertFalse({"YouTube", "Youtube"} <= set(self.formas))

    def test_sen_lixo(self):
        for lixo in ("$", "%", "+MAS+", "+RE@CIN", "A", "O", "N", "p. ex.", "Аэрофло́т", "OS\\", "A.C.CO.", "2M1207b"):
            with self.subTest(lixo=lixo):
                self.assertTrue(lixo not in self.formas, lixo)
        for f in self.formas:
            self.assertNotIn(" ", f)

    def test_frecuencias(self):
        # os nomes propios toman a frecuencia da súa forma en minúsculas (o corpus está en minúsculas)
        self.assertGreater(self.formas["Londres"], 0)
        self.assertGreater(self.formas["de"], self.formas["Londres"])
        # as formas verbais sen frecuencia quedan, con 0
        self.assertTrue("falariamos" in self.formas)


if __name__ == "__main__":
    unittest.main()
