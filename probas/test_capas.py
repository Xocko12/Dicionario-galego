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
