"""Capas opcionais e locucións: contido que ten que estar."""

import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def ler(nome):
    with (RAIZ / "datos" / nome).open(encoding="utf-8") as fh:
        return [json.loads(l) for l in fh]


class ProbasLocucions(unittest.TestCase):
    def test_locucions_da_rag(self):
        loc = {r["locucion"]: r for r in ler("locucions.jsonl")}
        for frase, categoria in (("a pesar de", "locución preposicional"), ("ao redor", "locución adverbial"),
                                 ("a miúdo", "locución adverbial"), ("de súpeto", "locución adverbial"),
                                 ("en canto a", "locución preposicional"), ("a sabendas", "locución adverbial")):
            with self.subTest(frase=frase):
                self.assertIn(frase, loc)
                self.assertIn(categoria, loc[frase]["categorias"])
        # as do VOLGa gardadas coa palabra clave diante quedan ben ordenadas
        self.assertNotIn("pesar de a", loc)


class ProbasCapas(unittest.TestCase):
    def test_toponimos(self):
        nomes = {r["nome"] for r in ler("capas/toponimos.jsonl")}
        for n in ("Santiago de Compostela", "A Coruña", "Ourense", "Pontevedra", "Lugo", "Vigo", "Fisterra"):
            self.assertIn(n, nomes)

    def test_siglas(self):
        siglas = {r["forma"]: r for r in ler("capas/siglas.jsonl")}
        self.assertIn("NIF", siglas)
        self.assertIn("fiscal", siglas["NIF"].get("nota", ""))

    def test_capas_lexicas_sen_repetir_o_nucleo(self):
        core = {r["id"] for r in ler("lemas.jsonl")}
        for capa in ("digalego", "comunidade", "terminoloxia"):
            with self.subTest(capa=capa):
                ids = [r["id"] for r in ler(f"capas/{capa}.jsonl")]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(core & set(ids), set())
                for r in ler(f"capas/{capa}.jsonl"):
                    if r["categoria"] == "verbo":
                        self.assertEqual(len(r["taboa"]["indicativo.presente"]), 6)

    def test_codigos(self):
        cod = {(r["codigo"], r["tipo"]) for r in ler("capas/codigos.jsonl")}
        self.assertIn(("glg", "iso639"), cod)
        self.assertIn(("EUR", "iso4217"), cod)


if __name__ == "__main__":
    unittest.main()


class ProbasSinonimos(unittest.TestCase):
    def test_sinonimos(self):
        sin = {}
        for r in ler("sinonimos.jsonl"):
            sin.setdefault(r["lema"], set()).update(x["forma"] for x in r["sinonimos"])
        self.assertIn("faldra", sin["aba"])
        self.assertIn("bastar", sin["abastar"])
        self.assertGreater(len(sin), 6000)


class ProbasSemantica(unittest.TestCase):
    def test_wordnet(self):
        w = {}
        for r in ler("capas/wordnet.jsonl"):
            w.setdefault(r["lema"], []).append(r)
        can = next(r for r in w["can"] if r["categoria"] == "substantivo")
        self.assertTrue(any("Canis" in x.get("definicion_en", "") for x in can["sentidos"]))
        self.assertTrue(any("perro" in x.get("es", []) for x in can["sentidos"]))
        self.assertGreater(len(w), 20000)

    def test_traducions(self):
        t = {}
        for r in ler("capas/traducions.jsonl"):
            t.setdefault(r["lema"], []).append(r)
        xanela = t["xanela"][0]
        self.assertIn("ventana", xanela["es"])
        self.assertIn("janela", xanela["pt"])
        self.assertIn("window", xanela["en"])
        self.assertIn("silla", t["cadeira"][0]["es"])


class ProbasDefinicions(unittest.TestCase):
    def test_definicions_galegas(self):
        ruta = RAIZ / "datos" / "capas" / "definicions-gl.jsonl"
        if not ruta.exists():
            self.skipTest("capa opcional non xerada")
        d = {}
        for r in ler("capas/definicions-gl.jsonl"):
            d.setdefault(r["lema"], []).append(r)
        casa = next(r for r in d["casa"] if r["categoria"] == "substantivo")
        self.assertEqual(casa["xenero"], "feminino")
        self.assertTrue(any("habita" in a["definicion"] for a in casa["acepcions"]))
        ledo = d["ledo"][0]
        self.assertIn("alegre", ledo["acepcions"][0].get("sinonimos", []))
        self.assertGreater(len(d), 30000)
        for rs in d.values():
            for r in rs:
                self.assertTrue(all("{{" not in a["definicion"] and "[[" not in a["definicion"] for a in r["acepcions"]), r["lema"])

    def test_definicions_inglesas(self):
        ruta = RAIZ / "datos" / "capas" / "definicions-en.jsonl"
        if not ruta.exists():
            self.skipTest("capa opcional non xerada")
        d = {r["lema"]: r for r in ler("capas/definicions-en.jsonl") if r["categoria"] == "substantivo"}
        self.assertTrue(any("house" in a["definicion"] for a in d["casa"]["acepcions"]))
        self.assertNotIn("falas", d)


class ProbasPlurais(unittest.TestCase):
    def test_sen_plurais_novos_fora_da_regra(self):
        import sys
        sys.path.insert(0, str(RAIZ / "ferramentas"))
        import anomalias_nominais
        self.assertEqual([p[0] for p in anomalias_nominais.buscar()], [])

    def test_correccions_de_flexion(self):
        lemas = {r["id"]: r for r in ler("lemas.jsonl")}
        self.assertEqual(lemas["cartafol#substantivo"]["formas"]["mp"], ["cartafois"])
        self.assertEqual(lemas["decibel#substantivo"]["formas"]["mp"], ["decibeis"])
        self.assertEqual(lemas["amábel#adxectivo"]["formas"]["mp"], ["amábeis"])
