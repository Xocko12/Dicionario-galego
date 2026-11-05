"""Táboas de referencia: se un cambio nas regras ou nas fontes as altera, a proba falla.

Para engadir un verbo revisado (p. ex. contra as normas da RAG), engade aquí as celas.
"""

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))

import conxugacion as C  # noqa: E402

REFERENCIA = {
    "falar": {
        "indicativo.presente": "falo falas fala falamos falades falan",
        "indicativo.copreterito": "falaba falabas falaba falabamos falabades falaban",
        "indicativo.preterito": "falei falaches falou falamos falastes falaron",
        "indicativo.antepreterito": "falara falaras falara falaramos falarades falaran",
        "indicativo.futuro": "falarei falarás falará falaremos falaredes falarán",
        "indicativo.pospreterito": "falaría falarías falaría falariamos falariades falarían",
        "subxuntivo.presente": "fale fales fale falemos faledes falen",
        "subxuntivo.preterito": "falase falases falase falásemos falásedes falasen",
        "subxuntivo.futuro": "falar falares falar falarmos falardes falaren",
        "infinitivo.conxugado": "falar falares falar falarmos falardes falaren",
    },
    "ser": {
        "indicativo.presente": "son es é somos sodes son",
        "indicativo.preterito": "fun fuches foi fomos fostes foron",
        "subxuntivo.presente": "sexa sexas sexa sexamos sexades sexan",
        "subxuntivo.futuro": "for fores for formos fordes foren",
    },
    "ir": {
        "indicativo.presente": "vou vas vai imos ides van",
        "indicativo.copreterito": "ía ías ía iamos iades ían",
        "subxuntivo.presente": "vaia vaias vaia vaiamos vaiades vaian",
    },
    "durmir": {"indicativo.presente": "durmo dormes dorme durmimos durmides dormen"},
    "facer": {"indicativo.preterito": "fixen fixeches fixo fixemos fixestes fixeron"},
    "pór": {"indicativo.presente": "poño pos pon pomos pondes poñen"},
    "traer": {"indicativo.copreterito": "traía traías traía traïamos traïades traían"},
    "ler": {"subxuntivo.presente": "lea leas lea leamos leades lean"},
    "crer": {"subxuntivo.presente": "crea creas crea creamos creades crean"},
    "erguer": {"subxuntivo.presente": "erga ergas erga ergamos ergades ergan"},
    # revisado contra o conxugador da RAG
    "prover": {
        "indicativo.presente": "provexo provés prové provemos provedes provén",
        "indicativo.copreterito": "provía provías provía proviamos proviades provían",
        "indicativo.preterito": "provín proviches proveu provemos provestes proveron",
        "indicativo.antepreterito": "provera proveras provera proveramos proverades proveran",
        "indicativo.futuro": "proverei proverás proverá proveremos proveredes proverán",
        "indicativo.pospreterito": "provería proverías provería proveriamos proveriades proverían",
        "subxuntivo.presente": "provexa provexas provexa provexamos provexades provexan",
        "subxuntivo.preterito": "provese proveses provese provésemos provésedes provesen",
        "subxuntivo.futuro": "prover proveres prover provermos proverdes proveren",
        "infinitivo.conxugado": "prover proveres prover provermos proverdes proveren",
    },
    "desprover": {"indicativo.presente": "desproveo desprovés desprové desprovemos desprovedes desprovén"},
    "seguir": {"indicativo.presente": "sigo segues segue seguimos seguides seguen"},
    "dicir": {"indicativo.antepreterito": "dixera dixeras dixera dixeramos dixerades dixeran"},
}

# imperativos confirmados co conxugador da RAG (os verbos con alternancia manteñen
# a vogal pechada da P1: durme, sube, sigue, fire)
IMPERATIVOS = {"falar": "fala", "ser": "sé", "vir": "ven", "durmir": "durme",
               "seguir": "sigue", "subir": "sube", "ferir": "fire", "vestir": "viste",
               "facer": "fai", "ter": "ten"}

PARTICIPIOS = {"dicir": "dito", "pór": "posto", "facer": "feito", "ver": "visto"}


def cargar():
    taboas = {}
    with (RAIZ / "datos" / "conxugacions.jsonl").open(encoding="utf-8") as fh:
        for liña in fh:
            v = json.loads(liña)
            taboas[v["lema"]] = v["taboa"]
    return taboas


class ProbasConxugacions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taboas = cargar()

    def test_referencia(self):
        for lema, tempos in REFERENCIA.items():
            for clave, esperado in tempos.items():
                with self.subTest(lema=lema, tempo=clave):
                    obtido = " ".join(c[0] if len(c) == 1 else "/".join(c) for c in self.taboas[lema][clave])
                    self.assertEqual(obtido, esperado)

    def test_imperativos(self):
        for lema, esperado in IMPERATIVOS.items():
            with self.subTest(lema=lema):
                self.assertEqual(self.taboas[lema]["imperativo"][1], [esperado])

    def test_participios(self):
        for lema, esperado in PARTICIPIOS.items():
            with self.subTest(lema=lema):
                self.assertEqual(self.taboas[lema]["participio"][0], esperado)

    def test_sen_encliticos(self):
        for lema, taboa in self.taboas.items():
            for forma, _, _ in C.formas(taboa):
                self.assertNotIn("-", forma, lema)


class ProbasEtiquetas(unittest.TestCase):
    def test_celas(self):
        self.assertEqual(C.celas((".", "is:presente", "P3", "/", "imperativo", "P2")),
                         [("indicativo.presente", 2), ("imperativo", 1)])
        self.assertEqual(C.celas((".", "is:subxuntivo", "presente", "P1", "/", "P3")),
                         [("subxuntivo.presente", 0), ("subxuntivo.presente", 2)])
        self.assertEqual(C.celas((".", "is:infinitivo", "/", "subxuntivo", "futuro", "P2")),
                         [("infinitivo.conxugado", 1), ("subxuntivo.futuro", 1)])

    def test_encliticos_ignorados(self):
        self.assertEqual(C.celas((".", "is:xerundio", "+", "enclítico")), [("xerundio", None)])
        self.assertEqual(C.celas((".", "is:pretérito", "P1", "[", "+", "enclítico", "]")),
                         [("indicativo.preterito", 0)])


if __name__ == "__main__":
    unittest.main()


class ProbasAnomalias(unittest.TestCase):
    def test_sen_anomalias_novas(self):
        import anomalias
        novas = anomalias.buscar()
        self.assertEqual({k: [x[0] for x in v] for k, v in novas.items()}, {})
