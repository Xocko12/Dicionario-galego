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
| Formas con pronomes enclíticos | 17 246 de uso real en `datos/` (*dime*, *dálle*, *díxocho*); ao construír, ~785 000 máis xeradas sistematicamente para os 600 verbos máis frecuentes (*díxoma*, *díxollelo*) |
| Nomes propios | 1 260 nomes de persoa da *Guía de nomes galegos* da RAG |
| Palabras gramaticais | artigos, 26 pronomes persoais, posesivos, demostrativos, indefinidos, relativos, interrogativos, exclamativos, 55 preposicións, 37 conxuncións e 50 contraccións coa súa composición (*do* = *de* + *o*, *cho* = *che* + *o*) |

| Locucións | 431 da RAG (*a pesar de*, *ao redor*, *de súpeto*), en `datos/locucions.jsonl` |

### Capas opcionais (`datos/capas/`)

Sobre o núcleo normativo hai capas separadas, cada unha coa súa procedencia
(`fontes/capas.json`), que as aplicacións poden incluír ou non:

| Capa | Contido | Rexistros |
|---|---|---|
| `digalego` | léxico do Digalego (Xunta) que non está na RAG, con flexión e conxugación | 3 043 (51 verbos) |
| `comunidade` | léxico de uso real achegado á comunidade de Hunspell-gl (informática, neoloxismos), sen revisión normativa | 816 (101 verbos) |
| `terminoloxia` | bUSCatermos (USC), TERGAL, Estraviz adaptado, Trasno, Wikipedia galega por áreas, unidades | 378 (19 verbos) |
| `siglas` | siglas, abreviaturas e símbolos coa súa expansión (Concello de Santiago, UDC, UVigo, CEG, Wikipedia, DRAG) | 2 157 |
| `toponimos` | lugares de Galicia, localidades, rexións e accidentes xeográficos (Wikipedia e Wiktionary galegos) | 24 071 |
| `antroponimos` | nomes e apelidos de persoa en contexto galego (INE revisado, Wikipedia e Wiktionary galegos) | 6 708 |
| `antroponimos-outras-linguas` | nomes de persoa en inglés, castelán, portugués e húngaro | 85 354 |
| `organizacions` | organizacións, obras, empresas, produtos (Wikipedia) | 10 354 |
| `codigos` | códigos ISO 639 (linguas) e ISO 4217 (moedas) | 8 258 |

Os verbos das capas léxicas pasan as mesmas comprobacións ca os do núcleo. Os
nomes compostos (*Santiago de Compostela*, *Galileo Galilei*) reconstrúense das
etiquetas de n-grama de Hunspell-gl. Todas as capas veñen de Hunspell-gl (GPL-3.0).

## Estrutura

```
datos/                  o catálogo (xerado e revisado)
  lemas.jsonl           un lema por liña (núcleo normativo: RAG)
  locucions.jsonl       locucións da RAG
  capas/                capas opcionais (Digalego, terminoloxía, siglas, topónimos...)
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

Que unha forma estea depende así de que alguén a dixese nunha película. Para os
**600 verbos máis frecuentes**, `construir.py` xera ademais **todas** as combinacións
regulares (forma verbal + un pronome, + *mo/cho/llo/nolo/volo/llelo* en catro
xéneros e números, + *se* + dativo), coas regras de Hunspell-gl, que colocan os
tiles e escollen *-lo*/*-no*. Son unhas 1 300 por verbo, así que non se gardan en
`datos/`: van ao SQLite (columna `orixe` = `corpus` | `sistematica`), ao teclado
(coa puntuación mínima, para que non desprazen as palabras de uso real) e ao Kobo.
Quedan fóra os verbos unipersoais e defectivos e calquera forma con dous tiles
(as raíces alternativas *háer*, *ír*, *érer* producen *háánllelo*, *érádela*).
`--encliticos N` cambia o número de verbos; `--encliticos 0` desactívao.

**Táboas de referencia.** `datos/correccions/referencia.json` contén as táboas
dos verbos irregulares e dos modelos de cada familia (*ser, estar, ter, haber,
ir, facer, dicir, dar, vir, ver, poder, querer, saber, caber, traer, valer,
pór/poñer, oír, saír, caer, ler, crer, rir, parir, durmir, subir, fuxir,
servir, seguir, sentir, mentir, pedir, construír, coñecer, continuar, pasear,
buscar, chegar, comezar, falar, comer, partir…*), escritas desde as Normas e o
conxugador da RAG. Mandan sobre as regras de Hunspell-gl e están protexidas por
`probas/test_referencia.py`. Ao aplicalas, só 2 verbos tiñan celas distintas do
que xeran as regras (*ir, pór*): os outros ~45 xa coincidían. Para ampliar a
referencia co conxugador da RAG, ver `docs/rag/README.md` e `ferramentas/comparar_rag.py`.

**Cantidade.** `probas/test_cobertura.py` comproba que todos os verbos dos módulos
da RAG teñen táboa (6 619), e as capas engaden os do Digalego, a comunidade e a
terminoloxía (171 máis).

**Comprobación independente dos tiles.** `ferramentas/acentuacion.py` implementa
as regras de acentuación das Normas sen usar Hunspell (sílaba tónica da forma
verbal, ditongos, hiatos, agudas/graves/esdrúxulas) e predí o til de cada forma
con enclíticos. Coincide con Hunspell-gl no 99,93 % das ~785 000 formas; nas que
non, revisadas unha a unha por familias, Hunspell é o que erra, agás nos tiles
diacríticos (*dáme*, *éche*, *pórcha*), que se conservan. Por iso, ao xerar as
formas, o til corríxese segundo as Normas e cada corrección queda rexistrada en
`dist/encliticos_corrixidos.tsv` para comunicala a Trasno. Familias corrixidas:
*vaiache → váiache*, *cainnos → caínnos*, *ria → ría*, *íreiche → ireiche*,
*estáslle → estaslle*, *estívela → estivela*, *dígamolo → digámolo* (esta última
tamén parcheada na regra, en `fontes/parches.json`).

Decisións tomadas onde a norma admite dúbida (revisadas, non cambiar sen motivo):
- o til regular pérdese cando a palabra deixa de ser aguda: *estache*, *estasme*,
  *iraslle*, *dela* (der + a), *teno*, *detena*;
- os tiles **diacríticos** consérvanse todos, non só *dáme* e *éche*: *vénme*,
  *véslle*, *sélle*, *pórlle*;
- *vai-a*, *cai-a*, *ensai-a* son dúas sílabas: *váiase*, *cáiache*, *ensáiame*;
- o imperativo só ten P2 e P5, agás *vamos* (ir): *vámonos*.

**`datos/nomes.jsonl`** — `{"nome": "Ádega", "tipo": "antropónimo", "fontes": ["rag-nomes"]}`

## Como se garante a calidade

- **Só fontes da RAG** no núcleo (`datos/lemas.jsonl`); o resto de módulos de
  Hunspell-gl van en capas separadas e etiquetadas (`datos/capas/`).
- **Comprobacións automáticas** en cada cambio (`.github/workflows/validar.yml`):
  - estrutura dos datos (`ferramentas/validar.py`);
  - táboas de referencia de verbos regulares e irregulares, pronomes,
    artigos e contraccións (`probas/`);
  - **patróns de conxugación** en todos os verbos (`ferramentas/anomalias.py`):
    p. ex. que o subxuntivo saia do presente (*busco → busque*, *fago → faga*)
    ou que P6 = P3 + *n*. As excepcións irregulares están revisadas en
    `datos/correccions/anomalias_revisadas.tsv`; calquera anomalía nova fai fallar as probas;
  - que **Hunspell recoñeza todas as formas** (`validar.py --hunspell`, con spylls);
  - **acentuación independente** das formas con enclíticos (`ferramentas/acentuacion.py`,
    ver arriba).
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
python3 ferramentas/importar.py      # rexenera datos/ (núcleo)
python3 ferramentas/capas.py         # rexenera datos/capas/
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
| `dicionario.sqlite` | Táboas `lemas` (con `capa`: `rag` = núcleo), `formas` (forma → lema + trazo gramatical), `encliticos` (~800 000, con `orixe`), `locucions`, `siglas`, `onomastica`, `codigos`, `nomes`. ~140 MB. |
| `teclado/gl_wordlist.combined` | ~1,3 millóns de palabras (núcleo, enclíticos, capas léxicas, siglas, topónimos e nomes galegos) con frecuencia no formato dos teclados AOSP; con `dicttool` convértese no `.dict` de HeliBoard e similares. |
| `teclado/palabras.tsv` | `forma<TAB>frecuencia`, para outros teclados. |
| `kobo/dicthtml-gl.zip` | Dicionario para Kobo: ao tocar unha forma (*dixeches*) abre o lema (*dicir*) coa súa categoría e conxugación. Pendente de probar nun dispositivo. |
| `kobo/galego.tsv` | O mesmo en formato tabulado (fonte dos tres seguintes, vía [pyglossary](https://github.com/ilius/pyglossary)). |
| `stardict/galego.*` | StarDict: GoldenDict (Linux/Windows/Android) e apps de dicionario de iOS e Android que lean StarDict. |
| `apple/Galego.apple/` | Fonte para **Dictionary.app de macOS**. Nun Mac, co *Dictionary Development Kit* (en *Additional Tools for Xcode*, gratuíto) instalado en `/Applications/Utilities/`: `cd Galego.apple && make && make install`. Despois actívase en Dictionary.app → Preferencias. Funciona co «Buscar» de tres dedos en todo macOS. |

**iOS** non permite engadir dicionarios ao «Buscar» do sistema; as opcións son unha
app de dicionario que lea StarDict, ou unha app propia co `dicionario.sqlite`.
Tampouco macOS nin iOS aceptan listas de palabras para o teclado do sistema.

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

- [ ] Definicións abertas (Wiktionary galego, CC BY-SA) como capa separada.
- [ ] Sinónimos (tesauro de LibreOffice para o galego).
- [ ] Ampliar as formas con enclíticos atestadas cun corpus maior.
- [ ] Revisar unha mostra das formas sistemáticas con enclíticos contra a RAG.
- [ ] Probar `apple/Galego.apple` nun Mac e o StarDict nunha app de iOS.
- [ ] Xerar o `.dict` do teclado e probar o dicionario Kobo nun dispositivo.
- [ ] Comunicar a Proxecto Trasno os erros atopados (borrador en `docs/informe-trasno.md`).
