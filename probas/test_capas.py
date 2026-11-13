"""Capas opcionais e locucións: contido que ten que estar."""

import json
import re
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

    def test_engadidos(self):
        # fontes/engadidos/*.dic: o que falta nos módulos de Hunspell-gl, coa fonte «engadidos»
        org = {r["nome"]: r for r in ler("capas/organizacions.jsonl")}
        for n in ("iOS", "iPhone", "Google", "Apple", "Microsoft", "Netflix", "Bizum", "Massimo Dutti"):
            self.assertIn(n, org)
        self.assertEqual(org["Google"]["fontes"], ["engadidos"])
        self.assertEqual(org["iOS"]["fontes"], ["comunidade"])
        siglas = {r["forma"]: r for r in ler("capas/siglas.jsonl")}
        self.assertIn("alta definición", siglas["HDMI"]["nota"])
        self.assertIn("5G", siglas)
        toponimos = {r["nome"] for r in ler("capas/toponimos.jsonl")}
        self.assertTrue({"Canberra", "Ulán Bátor", "Los Ángeles", "Londres"} <= toponimos)
        antroponimos = {r["nome"] for r in ler("capas/antroponimos.jsonl")}
        self.assertTrue({"Barack Obama", "Rosalía de Castro", "Ludwig van Beethoven", "Luís Tosar"} <= antroponimos)

    def test_cidades_clubs_e_nomes_doutras_linguas(self):
        cidades = {r["nome"] for r in ler("capas/cidades.jsonl")}
        self.assertTrue({"Yonkers", "A Coruña", "L'Hospitalet de Llobregat", "Donostia", "San Sebastián",
                         "Vila Nova de Gaia", "Lisboa", "Aguada de Cima", "Korschenbroich", "Leeds"} <= cidades)
        self.assertNotIn("Mumbai", cidades)   # en galego é Bombai (toponimos)
        self.assertFalse(any(n.endswith(" 02") for n in cidades))   # Lyon 02
        # os nomes ingleses das cidades con nome galego quedan fóra
        toponimos = {r["nome"] for r in ler("capas/toponimos.jsonl")}
        paises = {}
        for r in ler("capas/cidades.jsonl"):
            paises.setdefault(r["nome"], set()).add(r.get("nota", "").split(" (")[0])
        for n, pais in (("Vienna", "Austria"), ("Munich", "Germany"), ("Lisbon", "Portugal"), ("Berlin", "Germany"),
                        ("Paris", "France"), ("London", "United Kingdom"), ("Warsaw", "Poland"), ("Rome", "Italy"),
                        ("Moscow", "Russian Federation"), ("Beijing", "China"), ("Havana", "Cuba")):
            with self.subTest(nome=n):
                self.assertNotIn(pais, paises.get(n, set()))
        self.assertIn("Canada", paises["London"])   # London (Ontario) si: alí chámase así
        self.assertTrue({"Viena", "Múnic", "Lisboa", "Berlín", "París", "Londres"} <= toponimos)
        clubs = {r["nome"]: r for r in ler("capas/clubs.jsonl")}
        for n in ("Bayern", "Dortmund", "Celta", "Arenteiro", "Obradoiro", "Lakers", "Real Madrid", "Bayern München"):
            self.assertIn(n, clubs)
        self.assertIn("fútbol", clubs["Real Madrid"]["nota"])
        self.assertNotIn("Atl", clubs)          # abreviaturas das variantes
        nomes = {(r["nome"], r["tipo"]): r for r in ler("capas/nomes-outras-linguas.jsonl")}
        for n, t in (("John", "antropónimo"), ("Lennon", "apelido"), ("McCartney", "apelido"), ("Müller", "apelido"),
                     ("Jürgen", "antropónimo"), ("Jon", "antropónimo"), ("Ander", "antropónimo"), ("Pol", "antropónimo"),
                     ("Juan", "antropónimo"), ("João", "antropónimo"), ("Gonçalves", "apelido"), ("Etxeberria", "apelido"),
                     ("Jordi", "antropónimo"), ("François", "antropónimo"), ("Dupont", "apelido")):
            with self.subTest(nome=n):
                self.assertIn((n, t), nomes)
        self.assertIn("alemán", nomes[("Müller", "apelido")]["nota"])
        self.assertNotIn(("Mccartney", "apelido"), nomes)

    def test_lexico_cientifico_e_xuridico(self):
        term = {r["id"]: r for r in ler("capas/terminoloxia.jsonl")}
        for i in ("ibuprofeno#substantivo", "cortisol#substantivo", "copago#substantivo", "corresponsable#adxectivo",
                  "consensuar#verbo", "orzamentariamente#adverbio"):
            self.assertIn(i, term)
        self.assertEqual(term["ibuprofeno#substantivo"]["formas"]["mp"], ["ibuprofenos"])
        self.assertEqual(term["consensuar#verbo"]["taboa"]["indicativo.presente"][0], ["consensúo"])
        apertium = {r["id"]: r for r in ler("capas/apertium.jsonl")}
        ruta = RAIZ / "datos" / "capas" / "vocabularios.jsonl"
        lexico = {**({r["id"]: r for r in ler("capas/vocabularios.jsonl")} if ruta.exists() else {}), **apertium}
        self.assertEqual(lexico["corresponsabilidade#substantivo"]["formas"]["fp"], ["corresponsabilidades"])
        self.assertEqual(lexico["intermodal#adxectivo"]["formas"]["mp"], ["intermodais"])
        self.assertNotIn("edificatorio#adxectivo", apertium)      # paradigma mal aplicado na fonte
        wikt = {r["id"]: r for r in ler("capas/wiktionary.jsonl")}
        lexico.update(wikt)
        self.assertEqual(lexico["dopamina#substantivo"]["formas"], {"fs": ["dopamina"], "fp": ["dopaminas"]})
        self.assertNotIn("termodinámica#adxectivo", wikt)         # «forma feminina de termodinámico»
        self.assertNotIn("estructura#substantivo", wikt)           # grafía errada segundo Hunspell-gl
        core = {r["id"] for r in ler("lemas.jsonl")}
        for capa in ("apertium", "wiktionary"):
            ids = [r["id"] for r in ler(f"capas/{capa}.jsonl")]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(core & set(ids), set())

    def test_vocabularios(self):
        ruta = RAIZ / "datos" / "capas" / "vocabularios.jsonl"
        if not ruta.exists():
            self.skipTest("capa opcional non xerada (precisa pypdf e os PDF)")
        voc = {r["id"]: r for r in ler("capas/vocabularios.jsonl")}
        for i in ("epicondilite#substantivo", "ciclohexanona#substantivo", "ergodicidade#substantivo", "electrocinético#adxectivo"):
            self.assertIn(i, voc)
        self.assertEqual(voc["ciclohexanona#substantivo"]["xenero"], "feminino")
        self.assertNotIn("transpoñer#verbo", voc)                  # composto irregular: non vai por modelo
        self.assertFalse(any(r.get("baleiras") for r in voc.values()))
        core = {r["id"] for r in ler("lemas.jsonl")}
        self.assertEqual(core & set(voc), set())
        for r in voc.values():
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
        self.assertTrue(any("Canis" in x.get("definicion", "") for x in can["sentidos"]))
        # as definicións van en galego: nin o campo inglés nin as súas palabras
        ingles = re.compile(r"\b(the|of|and|with|which|that is|used for|having)\b")
        for rs in w.values():
            for r in rs:
                for x in r["sentidos"]:
                    self.assertNotIn("definicion_en", x)
                    self.assertTrue(x.get("definicion"), (r["lema"], x["ili"]))   # todos os sentidos, definidos en galego
                    self.assertFalse(ingles.search(x.get("definicion", "")), (r["lema"], x.get("definicion")))
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

    def test_sen_definicions_en_ingles(self):
        self.assertFalse((RAIZ / "datos" / "capas" / "definicions-en.jsonl").exists())

    def test_definicions_traducidas(self):
        ruta = RAIZ / "datos" / "capas" / "definicions-traducidas.jsonl"
        if not ruta.exists():
            self.skipTest("capa opcional non xerada")
        import sys
        sys.path.insert(0, str(RAIZ / "ferramentas"))
        import wiktionary
        existentes = wiktionary.definicions_existentes()
        ingles = re.compile(r"\b(the|of|and|with|which|that is|used for|having)\b")
        d = {}
        for r in ler("capas/definicions-traducidas.jsonl"):
            d.setdefault(r["lema"], []).append(r)
            vistas = set()
            for a in r["acepcions"]:
                self.assertFalse(ingles.search(a["definicion"]), (r["lema"], a["definicion"]))
                # nin repite o que xa di a capa definicions-gl nin se repite a si mesma
                normal = wiktionary._normal(a["definicion"])
                self.assertNotIn(normal, existentes.get(r["lema"], ()), r["lema"])
                self.assertNotIn(normal, vistas, r["lema"])
                vistas.add(normal)
        self.assertNotIn("falas", d)
        self.assertGreater(len(d), 8000)


class ProbasPlurais(unittest.TestCase):
    def test_sen_plurais_novos_fora_da_regra(self):
        import sys
        sys.path.insert(0, str(RAIZ / "ferramentas"))
        import anomalias_nominais
        self.assertEqual([p[0] for p in anomalias_nominais.buscar()], [])

    def test_correccions_de_flexion(self):
        lemas = {r["id"]: r for r in ler("lemas.jsonl")}
        # compostos dun monosílabo en -l: plural deste (fol/foles, mel/meles), como no DRAG
        self.assertEqual(lemas["cartafol#substantivo"]["formas"]["mp"], ["cartafoles"])
        self.assertEqual(lemas["chupamel#substantivo"]["formas"]["mp"], ["chupameles"])
        self.assertIn("decibeles", lemas["decibel#substantivo"]["formas"]["mp"])     # DRAG (o VOLGa: decibeis)
        self.assertEqual(lemas["amábel#adxectivo"]["formas"]["mp"], ["amábeis"])
