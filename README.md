# Dicionario galego aberto

Catálogo aberto e completo das palabras do galego normativo, coa súa flexión e
conxugación, pensado para construír ferramentas: teclados, dicionarios para
lectores electrónicos, correctores, conxugadores, xogos…

O vocabulario vén só de fontes da **Real Academia Galega**: o vocabulario do
Dicionario da RAG (DRAG) e o Vocabulario Ortográfico da Lingua Galega (VOLGa),
tal como os publica [Proxecto Trasno](https://gitlab.com/trasno/hunspell-gl)
con licenza GPL e permiso explícito do ILG-RAG. **Non inclúe definicións.**

## Contido

| | |
|---|---|
| Lemas | 53 402 (52 850 recomendados e 552 tolerados pola RAG) |
| Verbos | 6 619 coa conxugación completa (12 tempos e formas nominais) |
| Formas | 435 661 |
| Formas con pronomes enclíticos | 17 246 de uso real (*dime*, *dálle*, *díxocho*, *chámase*) |
| Nomes propios | 1 260 nomes de persoa da *Guía de nomes galegos* da RAG |
| Palabras gramaticais | artigos, 26 pronomes persoais, posesivos, demostrativos, indefinidos, relativos, interrogativos, exclamativos, 55 preposicións, 37 conxuncións e 50 contraccións coa súa composición (*do* = *de* + *o*, *cho* = *che* + *o*) |

Non se inclúen (polo de agora) siglas, abreviaturas nin locucións: nos módulos da
RAG de Hunspell-gl as locucións só están como palabras soltas, ás veces sen orde
(*pesar_de_a* por *a pesar de*), e as abreviaturas son as propias do dicionario
(*adv.*, *adx.*). Habería que tomalas doutra fonte.

## Estrutura

```
datos/                  o catálogo (xerado e revisado)
  lemas.jsonl           un lema por liña
  conxugacions.jsonl    táboa de conxugación de cada verbo
  encliticos.jsonl      formas verbais con pronomes enclíticos de uso real
  nomes.jsonl           nomes propios de persoa
  frecuencias.tsv       frecuencia de cada forma nun corpus
  correccions/          correccións manuais (revisadas)
fontes/
  fontes.json           fontes externas, versión, licenza e uso
  parches.json          erros corrixidos nas regras de Hunspell-gl
ferramentas/            scripts en Python (só biblioteca estándar)
probas/                 probas automáticas
```

## Formato dos datos

**`datos/lemas.jsonl`** — un obxecto JSON por liña:

```json
{"id": "casa#substantivo", "lema": "casa", "categoria": "substantivo", "xenero": "feminino",
 "formas": {"fs": ["casa"], "fp": ["casas"]}, "estado": "recomendado", "frecuencia": 1180,
 "fontes": ["drag", "volga"]}
{"id": "do#contracción", "lema": "do", "categoria": "contracción",
 "formas": {"ms": ["do"], "fs": ["da"], "mp": ["dos"], "fp": ["das"]},
 "composicion": ["de", "o"], "estado": "recomendado", "frecuencia": 12580, "fontes": ["drag", "volga"]}
```

| Campo | |
|---|---|
| `categoria` | `substantivo`, `adxectivo`, `verbo`, `adverbio`, `artigo`, `pronome_persoal`, `posesivo`, `demostrativo`, `indefinido`, `relativo`, `interrogativo`, `exclamativo`, `numeral`, `preposición`, `conxunción`, `interxección`, `contracción` |
| `formas` | `ms`, `fs`, `mp`, `fp` (masculino/feminino, singular/plural) |
| `tipos` | verbos: `transitiva`, `intransitiva`, `pronominal`, `defectivo`, `unipersoal`… |
| `estado` | `recomendado` ou `tolerado` (segundo a RAG) |
| `fontes` | `drag` e/ou `volga`. Se está nos dous, os datos son os do DRAG |
| `frecuencia` | aproximada, para ordenar (p. ex. suxestións dun teclado) |

**`datos/conxugacions.jsonl`** — unha táboa por verbo:

```json
{"lema": "falar", "fontes": ["hunspell-gl"], "taboa": {
  "indicativo.presente": [["falo"], ["falas"], ["fala"], ["falamos"], ["falades"], ["falan"]],
  "...": "...", "xerundio": ["falando"], "participio": ["falado", "falados", "falada", "faladas"]}}
```

Cada tempo ten 6 celas (P1–P6) e cada cela é unha lista porque hai variantes
(*tendes*/*tedes*). Os tempos seguen a terminoloxía da RAG: presente,
copretérito, pretérito, antepretérito, futuro e pospretérito de indicativo;
presente, pretérito e futuro de subxuntivo; imperativo (P2 e P5); infinitivo
conxugado. `correccions` indica as celas corrixidas a man.

**`datos/encliticos.jsonl`** — formas con pronomes enclíticos:

```json
{"forma": "díxocho", "lema": "dicir", "base": ["indicativo.preterito.P3"], "pronomes": ["che", "o"], "frecuencia": 2}
```

Hunspell-gl pode xerar máis de 160 millóns de combinacións de verbo + pronomes,
moitas tan forzadas como *falándochello*. Só se gardan as que **aparecen no corpus**,
**non son xa unha forma simple** (*abríramos* é antepretérito, non *abríra* + *mos*;
*poderíamos* é a grafía anterior a 2003 de *poderiamos*), teñen a **parte verbal
coherente coa táboa corrixida** e levan un pronome, unha contracción de dativo +
acusativo (*mo*, *cho*, *llo*, *nolo*, *volo*, *llelo*) ou *se* + dativo (*díxoselle*).
Unha forma ambigua aparece unha vez por cada análise (*sorpréndenos* = *sorprende* +
*nos* ou *sorprenden* + *os*).

**`datos/nomes.jsonl`** — `{"nome": "Ádega", "tipo": "antropónimo", "fontes": ["rag-nomes"]}`

## Como se garante a calidade

- **Só fontes da RAG** para o vocabulario; o resto de módulos de Hunspell-gl
  (Wikipedia, terminoloxías, nomes…) non se usan.
- **Comprobacións automáticas** en cada cambio (`.github/workflows/validar.yml`):
  - estrutura dos datos (`ferramentas/validar.py`);
  - táboas de referencia de verbos regulares e irregulares, pronomes,
    artigos e contraccións (`probas/`);
  - **patróns de conxugación** en todos os verbos (`ferramentas/anomalias.py`):
    p. ex. que o subxuntivo saia do presente (*busco → busque*, *fago → faga*)
    ou que P6 = P3 + *n*. As excepcións irregulares están revisadas en
    `datos/correccions/anomalias_revisadas.tsv`; calquera anomalía nova fai fallar as probas;
  - que **Hunspell recoñeza todas as formas** (`validar.py --hunspell`, con spylls).
- **Erros atopados en Hunspell-gl e corrixidos** (convén comunicalos a Trasno):
  *ler/crer* (*la* → *lea*, *cra* → *crea*), *erguer* (*ergugan* → *ergan*),
  *dicir* (antepretérito etiquetado como pospretérito), *pór* (táboa incompleta),
  imperativo dos verbos con alternancia vocálica (*sube* → *sobe*, *durme* → *dorme*,
  *sigue* → *segue*), *prover* (revisado co conxugador da RAG), entre outros. Ver `fontes/parches.json` e
  `datos/correccions/conxugacions.json`.

## Uso

Precisa Python 3.10 ou superior.

```sh
python3 ferramentas/descargar.py     # descarga as fontes en fontes/cache/
python3 ferramentas/importar.py      # rexenera datos/
python3 ferramentas/validar.py       # estrutura
python3 ferramentas/anomalias.py     # patróns de conxugación
python3 -m unittest discover -s probas

pip install -r requirements.txt      # para o seguinte
python3 ferramentas/validar.py --hunspell
python3 ferramentas/construir.py --kobo
```

## Produtos (`dist/`)

`ferramentas/construir.py` xera, a partir de `datos/`:

| Ficheiro | Para que serve |
|---|---|
| `dicionario.sqlite` | Táboas `lemas`, `formas` (forma → lema + trazo gramatical), `encliticos` e `nomes`. |
| `teclado/gl_wordlist.combined` | Lista de palabras (con enclíticos e nomes) con frecuencia no formato dos teclados AOSP; con `dicttool` convértese no `.dict` de HeliBoard e similares. |
| `teclado/palabras.tsv` | `forma<TAB>frecuencia`, para outros teclados. |
| `kobo/dicthtml-gl.zip` | Dicionario para Kobo: ao tocar unha forma (*dixeches*) abre o lema (*dicir*) coa súa categoría e conxugación. Pendente de probar nun dispositivo. |
| `kobo/galego.tsv` | O mesmo en formato tabulado, para converter con [pyglossary](https://github.com/ilius/pyglossary) a StarDict, MDict… |

## Fontes e licenzas

| Fonte | Licenza | Uso |
|---|---|---|
| Vocabulario do DRAG e VOLGa, vía [Hunspell-gl](https://gitlab.com/trasno/hunspell-gl) (Proxecto Trasno), versión fixada en `fontes/fontes.json` | GPL-3.0 | lemas, categorías, flexión e conxugación |
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles 2018) | CC BY-SA 4.0 | frecuencias |
| Revisión manual | GPL-3.0 | correccións segundo as *Normas ortográficas e morfolóxicas do idioma galego* (RAG/ILG) |

Todo o proxecto (datos e código) publícase baixo a **GPL-3.0 ou posterior**
(`LICENSE`).

## Como contribuír

- **Corrixir unha conxugación**: engade a cela en `datos/correccions/conxugacions.json`
  cunha `nota`, executa `ferramentas/importar.py` e engade o verbo ás táboas de
  referencia de `probas/test_conxugacions.py`.
- **Revisar contra a RAG**: compara a táboa dun verbo co conxugador da RAG; se
  coincide, engádea ás probas de referencia para que quede protexida.

## Folla de ruta

- [ ] Locucións, siglas e abreviaturas de uso xeral (precisan outra fonte).
- [ ] Ampliar as formas con enclíticos cun corpus maior.
- [ ] Xerar o `.dict` do teclado e probar o dicionario Kobo nun dispositivo.
- [ ] Comunicar a Proxecto Trasno os erros atopados.
