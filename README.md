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
| Verbos | 6 619 coa conxugación completa (12 tempos e formas nominais); **6 522 coa táboa do conxugador da RAG** como referencia (os demais non teñen conxugador na RAG) |
| Formas | 435 661 |
| Diminutivos | 100 736 formas en *-iño/-iña* de 30 024 substantivos (*gatiño, casiña, amiguiño, canciño, irmanciña, persoíña*) e 13 695 adxectivos (*pobriño, quentiña, bonitiño, boíño*), xeradas coas regras de `ferramentas/diminutivos.py` |
| Formas con pronomes enclíticos | 17 246 de uso real en `datos/` (*dime*, *dálle*, *díxocho*); ao construír, ~785 000 máis xeradas sistematicamente para os 600 verbos máis frecuentes (*díxoma*, *díxollelo*) |
| Nomes propios | 1 260 nomes de persoa da *Guía de nomes galegos* da RAG |
| Palabras gramaticais | artigos, 26 pronomes persoais, posesivos, demostrativos, indefinidos, relativos, interrogativos, exclamativos, 55 preposicións, 37 conxuncións e 50 contraccións coa súa composición (*do* = *de* + *o*, *cho* = *che* + *o*) |

| Locucións | 431 da RAG (*a pesar de*, *ao redor*, *de súpeto*), en `datos/locucions.jsonl` |
| Sinónimos | 6 997 entradas do thesaurus do VOLGa (GPL), en `datos/sinonimos.jsonl`, con marca das formas toleradas |
| Sentidos (WordNet) | 27 137 sentidos de 23 409 lemas (Galnet, CC BY): definición en inglés, sinónimos galegos, equivalentes es/pt/en |
| Traducións | 30 427 lemas con equivalentes en castelán (25 718), portugués (5 430) e inglés (13 914), de Apertium (GPL) |
| Definicións en galego | 44 125 entradas (74 737 acepcións) do Wiktionary galego, con exemplos, sinónimos e antónimos por acepción (CC BY-SA) |
| Definicións en inglés | 21 035 entradas galegas do Wiktionary inglés (CC BY-SA) |
| Separación silábica | patróns `hyph_gl.dic` de Trasno, en `dist/hyphenation/` |

### Definicións

O contido do dicionario da RAG ten dereitos de autor e non se copia. As fontes
abertas de definicións son:

| Capa | Fonte | Licenza | Estado |
|---|---|---|---|
| `wordnet` | Galnet (Open Multilingual Wordnet): cada sentido coa **definición en inglés** do WordNet de Princeton, os sinónimos galegos e os equivalentes es/pt/en | CC BY 3.0 | **feita** (`ferramentas/wordnet.py`) |
| `traducions` | Apertium es-gl, spa-glg, pt-gl, en-gl | GPL | **feita** (`ferramentas/traducions.py`) |
| `definicions-gl` | **Wiktionary galego**: definicións en galego, con exemplos, sinónimos e antónimos por acepción | CC BY-SA 4.0 | **feita**: 44 125 entradas, 74 737 acepcións (`ferramentas/wiktionary.py`) |
| `definicions-en` | Wiktionary inglés (entradas galegas, vía kaikki.org): definicións en inglés, con exemplos | CC BY-SA 4.0 | **feita**: 21 035 entradas (sen as entradas de formas flexionadas) |

As dúas capas de Wiktionary xéranse con `ferramentas/wiktionary.py --descargar &&
ferramentas/wiktionary.py` (precisa acceso a dumps.wikimedia.org e kaikki.org; non
se rexeneran na integración continua: actualízanse a man de cando en vez). O
analizador do Wiktionary galego segue os modelos reais das páxinas e descarta
calquera acepción con restos de wikitexto. Non hai capa de definicións da RAG: o
seu dicionario ten dereitos de autor. O Kobo, StarDict e Apple mostran as
definicións galegas, as inglesas, as traducións e os sentidos do WordNet.

### Capas opcionais (`datos/capas/`)

Sobre o núcleo normativo hai capas separadas, cada unha coa súa procedencia
(`fontes/capas.json`), que as aplicacións poden incluír ou non:

| Capa | Contido | Rexistros |
|---|---|---|
| `digalego` | léxico do Digalego (Xunta) que non está na RAG, con flexión e conxugación | 3 043 (51 verbos) |
| `comunidade` | léxico de uso real achegado á comunidade de Hunspell-gl (informática, neoloxismos), sen revisión normativa | 816 (101 verbos) |
| `terminoloxia` | bUSCatermos (USC), TERGAL, Estraviz adaptado, Trasno, Wikipedia galega por áreas, unidades; máis 488 engadidos a man: ciencia e substancias (*ibuprofeno, cortisol, grafeno, nanopartícula*) e léxico xurídico e administrativo atestado no Parlamento de Galicia (*copago, gobernanza, corresponsable, consensuar*) | 865 (73 verbos) |
| `vocabularios` | termos dos vocabularios terminolóxicos galegos en PDF que non están na RAG nin nas capas anteriores: *Termos esenciais* da USC (dereito administrativo, civil e laboral; acceso aberto), 16 vocabularios da UDC (dereito, matemáticas, física e química, electricidade, biblioteconomía, podoloxía, fisioterapia, deportes…), UVigo (xurídico-administrativo, informática), Termigal/CIRP (alimentación e restauración, recursos humanos), RAG (televisión), Realiter (léxicos panlatinos). Só os termos, coa categoría e o xénero que dá cada obra; as definicións non se copian. Xérase con pypdf (`fontes/cache/derivados/vocabularios.dic`) | 5 432 (199 verbos) |
| `apertium` | léxico do dicionario monolingüe de Apertium (GPL) que non está na RAG nin nas capas anteriores: substantivos, adxectivos e adverbios coa flexión dos seus paradigmas (*corresponsabilidade, fiscalidade, intermodal*) | 1 599 |
| `wiktionary` | léxico do Wiktionary galego (capa `definicions-gl`) que non está na RAG nin nas capas anteriores: substantivos, adxectivos e adverbios coa flexión regular (*dopamina, anisotrópico, magnetopausa*) | 3 468 |
| `siglas` | siglas, abreviaturas e símbolos coa súa expansión (Concello de Santiago, UDC, UVigo, CEG, Wikipedia, DRAG); máis 285 engadidas a man (*HDMI, 5G, IA, QR, IVA, ERTE, CELGA, OCDE, TDAH*…) | 9 313 |
| `toponimos` | lugares de Galicia, localidades, rexións e accidentes xeográficos (Wikipedia e Wiktionary galegos); máis 42 capitais e cidades engadidas a man | 24 113 |
| `antroponimos` | nomes e apelidos de persoa en contexto galego (INE revisado, Wikipedia e Wiktionary galegos); máis 2 635 persoas coñecidas engadidas a man (política, deporte, música, cine, ciencia, arte, letras galegas e universais) | 9 343 |
| `antroponimos-outras-linguas` | nomes de persoa en inglés, castelán, portugués e húngaro | 85 354 |
| `organizacions` | organizacións, obras, empresas, produtos (Wikipedia); máis 2 476 engadidos a man: empresas, produtos e servizos tecnolóxicos (*Google, Apple, iOS, Windows, Netflix, Bizum*…), institucións, medios, entidades (*Xunta, Inditex, Sergas*…) e marcas (coches e modelos, roupa, alimentación, bebidas, cosmética, fogar: *Toyota, Golf, Levi's, Nutella*…) | 12 830 |
| `clubs` | clubs de fútbol do mundo (football.db de openfootball, CC0; só os nomes e as súas variantes) cos seus nomes curtos (*Bayern, Dortmund, Celta*); máis clubs galegos e doutros deportes e competicións engadidos a man (*Arenteiro, Obradoiro, Lakers, Euroliga*) | 8 888 |
| `cidades` | cidades do mundo con máis de 15 000 habitantes (GeoNames, CC BY), os municipios de España (INE) e os concellos e freguesías de Portugal (CAOP). GeoNames dá en inglés os nomes das cidades famosas (*Vienna, Munich, Beijing*): quedan fóra se son palabras do dicionario inglés fóra dos países de fala inglesa, ou se só se distinguen dun topónimo galego polos acentos (*Berlin/Berlín*); o nome galego está en `toponimos` | 42 729 |
| `nomes-outras-linguas` | nomes de pía e apelidos correntes noutras linguas, dunha palabra: inglés (SSA, ONS, Census), alemán (Destatis), francés (INSEE), portugués (INE), catalán (Idescat), vía damegender (GPL); máis éuscaro, catalán, castelán, francés e alemán engadidos a man | 41 694 |
| `codigos` | códigos ISO 639 (linguas) e ISO 4217 (moedas) | 8 258 |
| `wordnet` | sentidos de Galnet (ver «Definicións») | 23 409 |
| `traducions` | equivalentes es/pt/en de Apertium | 30 427 |

Os verbos das capas léxicas pasan as mesmas comprobacións ca os do núcleo. Os
nomes compostos (*Santiago de Compostela*, *Galileo Galilei*) reconstrúense das
etiquetas de n-grama de Hunspell-gl. As capas de Hunspell-gl son GPL-3.0; a de
WordNet, CC BY 3.0; a de Apertium, GPL-2.0.

As capas `vocabularios`, `apertium`, `wiktionary`, `cidades`, `clubs` e `nomes-outras-linguas` non veñen de Hunspell-gl senón
doutras fontes abertas (`fontes/fontes.json`, fixadas por *commit*; clave `importador` en
`fontes/capas.json`, funcións de `ferramentas/capas.py`).

O que falta nas fontes engádese a man en `fontes/engadidos/<capa>.dic`, no mesmo
formato dos módulos de Hunspell-gl (`Nome po:nome_propio  # nota`; nos nomes compostos,
cada palabra na súa liña con `is:ngrama_Nome_Completo`); `fontes/capas.json` indica en
`engadidos` a que capa vai cada ficheiro e os rexistros levan a fonte `engadidos`.

## Estrutura

```
datos/                  o catálogo (xerado e revisado)
  lemas.jsonl           un lema por liña (núcleo normativo: RAG)
  locucions.jsonl       locucións da RAG
  sinonimos.jsonl       sinónimos (thesaurus do VOLGa)
  capas/                capas opcionais (Digalego, terminoloxía, siglas, topónimos...)
  conxugacions.jsonl    táboa de conxugación de cada verbo
  encliticos.jsonl      formas verbais con pronomes enclíticos de uso real
  nomes.jsonl           nomes propios de persoa
  frecuencias.tsv       frecuencia de cada forma nun corpus
  correccions/          correccións manuais (revisadas); teclado.json: nomes que mandan sobre a palabra común homógrafa
fontes/
  fontes.json           fontes externas, versión, licenza e uso
  capas.json            capas opcionais: módulos de Hunspell-gl e engadidos propios
  parches.json          erros corrixidos nas regras de Hunspell-gl
  engadidos/            palabras engadidas a man (formato dos módulos de Hunspell-gl)
ferramentas/            scripts en Python (só biblioteca estándar)
probas/                 probas automáticas
```

## Formato dos datos

**`datos/lemas.jsonl`** — un obxecto JSON por liña:

```json
{"id": "casa#substantivo", "lema": "casa", "categoria": "substantivo", "xenero": "feminino",
 "formas": {"fs": ["casa"], "fp": ["casas"]}, "diminutivos": {"fs": ["casiña"], "fp": ["casiñas"]},
 "estado": "recomendado", "frecuencia": 1180, "fontes": ["drag", "volga"]}
{"id": "do#contracción", "lema": "do", "categoria": "contracción",
 "formas": {"ms": ["do"], "fs": ["da"], "mp": ["dos"], "fp": ["das"]},
 "composicion": ["de", "o"], "estado": "recomendado", "frecuencia": 12580, "fontes": ["drag", "volga"]}
```

| Campo | |
|---|---|
| `categoria` | `substantivo`, `adxectivo`, `verbo`, `adverbio`, `artigo`, `pronome_persoal`, `posesivo`, `demostrativo`, `indefinido`, `relativo`, `interrogativo`, `exclamativo`, `numeral`, `preposición`, `conxunción`, `interxección`, `contracción` |
| `formas` | `ms`, `fs`, `mp`, `fp` (masculino/feminino, singular/plural) |
| `diminutivos` | substantivos e adxectivos: as formas en *-iño/-iña*, coas mesmas claves ca `formas` (ver «Diminutivos») |
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

**Conxugador da RAG.** `ferramentas/comparar_rag.py --rag --todos --aceptar` descarga
a táboa de cada verbo do conxugador de academia.gal (con calma, 1 petición por
segundo) e gárdaa en `datos/referencia-rag.json`: esas táboas mandan sobre todo
o demais e `probas/test_referencia.py` comproba que os datos coincidan con elas.
6 522 dos 6 790 verbos do catálogo teñen táboa na RAG (os outros son do Digalego,
da comunidade ou verbos sen conxugador, como *soer*). A comparación atopou e
corrixiu, entre outros, participios irregulares (*aberto*, *aceso/acendido*,
*apreso/aprendido*), paradigmas incompletos (*argüír*, *pracer*) e o imperativo
dos verbos con alternancia vocálica (*durme, sube, sigue, fire, viste*). Tamén
atopou erros nos datos do propio conxugador, que non se aceptan e quedan
documentados en `docs/rag/excluidos.json` para comunicarllos á RAG (P6 do
presente de *pór* e compostos dada como *pon/supón*; *alancañar* con subxuntivo de
*alancar*; *desouvir*; *despir*). As diferenzas restantes están en `docs/rag/diferenzas.tsv`.

**Timbre vocálico.** O conxugador marca as vogais tónicas abertas (*toses [ɔ]*,
*cuberto [ɛ]*); gárdanse en `datos/timbre.tsv` (8 709 formas), útiles para
pronuncia e síntese de voz.

**Táboas de referencia manuais.** `datos/correccions/referencia.json` contén as táboas
dos verbos irregulares e dos modelos de cada familia (*ser, estar, ter, haber,
ir, facer, dicir, dar, vir, ver, poder, querer, saber, caber, traer, valer,
pór/poñer, oír, saír, caer, ler, crer, rir, parir, durmir, subir, fuxir,
servir, seguir, sentir, mentir, pedir, construír, coñecer, continuar, pasear,
buscar, chegar, comezar, falar, comer, partir…*), escritas desde as Normas e o
conxugador da RAG (44 verbos), máis as dos **compostos** derivadas delas
(`ferramentas/compostos.py`: *manter* como *ter*, *convir* como *vir*, *supor* como
*pór*, *desfacer*, *predicir*, *prever*, *sobresaír*, *conseguir*…, ~110 verbos, co til
recalculado: *ten → mantén*, *di → predí*). Mandan sobre as regras de Hunspell-gl e
están protexidas por `probas/test_referencia.py`. Ao aplicalas, dos 44 verbos escritos
só 2 tiñan celas distintas do que xeran as regras (*ir, pór*); nos compostos
corrixiuse o pretérito dos de *vir* (Hunspell admitía *conviu* xunto a *conveu*).
A comparación tamén serviu ao revés: os compostos de *traer* **non** se derivan,
porque teñen pretérito regular (*contraeu*), como ben facía Hunspell. Para ampliar a
referencia co conxugador da RAG, ver `docs/rag/README.md` e `ferramentas/comparar_rag.py`
(`--rag --todos` descarga e compara todos os verbos co conxugador de academia.gal).

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

**Diminutivos.** Hunspell-gl non ten regras de diminutivo, así que `ferramentas/diminutivos.py`
xéraos para cada substantivo e adxectivo do núcleo seguindo a ortografía das Normas. O sufixo é tónico, polo
que a base perde o til (*árbore → arboriña*, *música → musiquiña*), e:

- nas palabras en vogal átona, esta cae: *gato → gatiño*, *casa → casiña*, *noite → noitiña*
  (*-iño* no masculino e *-iña* no feminino); os masculinos en *-a* conservan o *-a*
  (*problema → problemiña*, atestado no corpus);
- cambios gráficos: *barco → barquiño*, *amigo → amiguiño*, *praza → praciña*,
  *lingua → lingüiña*; o ditongo átono final cae: *historia → historiña*, *espacio → espaciño*;
- se a base queda en vogal, o *i* leva til polo hiato: *persoa → persoíña*, *rúa → ruíña*,
  *café → cafeíño*, *avó → avoíño*, e nos monosílabos: *bo → boíño* (atestado); os femininos en
  *-á* de *-án* fan *-anciña* (*irmá → irmanciña*, *chá → chanciña*), os demais *-aíña* (*má → maíña*);
- *-n* e ditongo final: *-ciño/-ciña* (*can → canciño*, *irmán → irmanciño*, *nai → naiciña*);
  *-r*, *-l*, *-z*, *-s* agudo: *flor → floriña*, *papel → papeliño*, *rapaz → rapaciño*, *país → paisiño*;
- os adxectivos invariables levan os dous xéneros: *pobre → pobriño, pobriña*;
  *quente → quentiño, quentiña*; *azul → azuliño, azuliña*.

Non se dá diminutivo cando a forma resultante xa é outra palabra do catálogo, porque eses
homógrafos teñen a súa entrada: *cociña* non é diminutivo de *coza*, nin *golfiño* de *golfo*,
nin *camiña* (de *camiñar*) de *cama*; *noitiña*, *carriño* e *pequeniño* son lemas da RAG. Tampouco nos
femininos en *-o* (*foto, moto*: sen uso atestado), nas palabras graves en *-s* (*lapis*), nas
rematadas en ditongo + vogal (*raio*), noutras consoantes (*álbum*) nin nas que teñen guión. As
regras compróbanse en `probas/test_diminutivos.py`; das formas do corpus en *-iño/-iña* que non
xeran, case todas son de indefinidos e adverbios (*pouquiño, mesmiño, todiño, amodiño*), que polo
de agora non levan diminutivo.

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
  *prover* (revisado co conxugador da RAG), entre outros. (Unha «corrección» nosa
  anterior, *durme/sube/sigue* → *dorme/sobe/segue*, era errada: o conxugador da RAG
  confirma *durme, sube, sigue, fire*; retirouse.) Ver `fontes/parches.json` e
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
sh ferramentas/compilar_dicttool.sh  # opcional: para teclado/main_gl.dict
python3 ferramentas/validar.py --hunspell
python3 ferramentas/construir.py --kobo
```

## Produtos (`dist/`)

`ferramentas/construir.py` xera, a partir de `datos/`:

| Ficheiro | Para que serve |
|---|---|
| `dicionario.sqlite` | Táboas `lemas` (con `capa`: `rag` = núcleo), `formas` (forma → lema + trazo gramatical; os diminutivos co trazo `diminutivo.ms`, `diminutivo.fp`…), `encliticos` (~800 000, con `orixe`), `locucions`, `sinonimos`, `sentidos` (WordNet), `traducions`, `definicions`, `siglas`, `onomastica`, `codigos`, `nomes`. ~150 MB. |
| `teclado/gl_wordlist.combined` | ~1,4 millóns de palabras (núcleo, enclíticos, capas léxicas, siglas, topónimos, cidades, antropónimos, nomes doutras linguas, organizacións, marcas, clubs e nomes galegos) con frecuencia no formato dos teclados AOSP; con `dicttool` convértese no `.dict` de HeliBoard e similares. Dos nomes compostos entran as palabras con maiúscula (*York*, *Compostela*, *Einstein*). **Non entra ningún nome propio nin sigla que sexa unha palabra común escrita con maiúsculas** (*ISO*, *Iso*, *Como*, *Paz*, *SE*, *A*): o corpus de frecuencias está en minúsculas, así que tiñan a mesma frecuencia ca *iso*, *como*, *paz*, *se* e *a*, e ao deslizar o teclado escribía a maiúscula. A maiúscula ponna quen escribe e o teclado aplícaa á suxestión. Os nomes que só veñen das capas foráneas (`cidades`, `clubs` de fóra, `nomes-outras-linguas`, `antroponimos-outras-linguas`) e non aparecen no corpus levan a frecuencia mínima (`f=1`), por debaixo de calquera palabra ou nome galego (`f=10` sen uso no corpus). Excepcións revisadas a man en `datos/correccions/teclado.json` (*Londres* sobre a forma verbal *londres*, *Luís* sobre a moeda, *Brasil*, *Xunta*…): entra o nome e a palabra común queda con frecuencia 0. |
| `teclado/main_gl.dict` | **Dicionario do teclado** (formato binario AOSP v2) para HeliBoard e outros teclados baseados no de AOSP: en HeliBoard, Axustes > Idiomas > Galego > Engadir dicionario. Xérase só se existe `fontes/cache/dicttool_aosp.jar` (`sh ferramentas/compilar_dicttool.sh` compílao desde o código de Android; precisa un JDK). A última versión está tamén no repositorio, en `teclado/main_gl.dict`, e nas *releases*. |
| `teclado/palabras.tsv` | `forma<TAB>frecuencia`, para outros teclados. |
| `kobo/dicthtml-gl.zip` | Dicionario para Kobo: ao tocar unha forma (*dixeches*) abre o lema (*dicir*) coa súa categoría, conxugación, sinónimos, traducións, sentidos do WordNet e, cando existan, as definicións do Wiktionary. Pendente de probar nun dispositivo. |
| `kobo/galego.tsv` | O mesmo en formato tabulado (fonte dos tres seguintes, vía [pyglossary](https://github.com/ilius/pyglossary)). |
| `stardict/galego.*` | StarDict: GoldenDict (Linux/Windows/Android) e apps de dicionario de iOS e Android que lean StarDict. |
| `hunspell/gl_ES.dic` + `gl_ES.aff` | **Corrector ortográfico** para macOS (Pages, Mail, Safari…: copiar a `~/Library/Spelling/` substituíndo calquera `gl_ES` anterior, e escoller «Galego» en Axustes > Teclado > Ortografía), LibreOffice, Firefox, Thunderbird. Coa estrutura de Hunspell-gl (regras e dicionario de Trasno cos módulos da RAG e as nosas correccións ás regras), máis as nosas formas que esa base non recoñece (os mesmos nomes propios ca o teclado: topónimos, cidades, antropónimos, nomes doutras linguas, organizacións, marcas e clubs; siglas, capas léxicas, formas revisadas coa RAG) e, marcadas como **prohibidas**, as que Hunspell-gl acepta pero están mal segundo o conxugador da RAG (*cubrido*, *conviron*, *éras*, *vaiache*…; lista en `hunspell/prohibidas.tsv`). Non vale para iOS/iPadOS. |
| `hyphenation/hyph_gl.dic` | Patróns de separación silábica (orixinal ISO-8859-1 e copia UTF-8), para LibreOffice, a biblioteca Hyphen e lectores electrónicos. |
| `apple/Galego.apple/` | Fonte para **Dictionary.app de macOS**. Nun Mac, co *Dictionary Development Kit* (en *Additional Tools for Xcode*, gratuíto) instalado en `/Applications/Utilities/`: `cd Galego.apple && make && make install` (o Makefile xa usa o formato 10.11; sen o kit en `/Applications/Utilities/`, `make DICT_BUILD_TOOL_DIR=/ruta/ao/kit`). Despois actívase en Dictionary.app → Axustes. Funciona co «Buscar» de tres dedos en todo macOS: ao buscar unha forma (*dixeches*, *díxocho*) ábrese o lema. Probado en macOS 27 (~210 MB instalado) e en Mac OS X 10.7 Lion, compilado con `make DICT_BUILD_OPTS="-v 10.6"` e copiado a `~/Library/Dictionaries/`. |

**iOS** non permite engadir dicionarios ao «Buscar» do sistema; as opcións son unha
app de dicionario que lea StarDict, ou unha app propia co `dicionario.sqlite`.
Tampouco macOS nin iOS aceptan listas de palabras para o teclado do sistema.

## Fontes e licenzas

| Fonte | Licenza | Uso |
|---|---|---|
| Vocabulario do DRAG e VOLGa, vía [Hunspell-gl](https://gitlab.com/trasno/hunspell-gl) (Proxecto Trasno), versión fixada en `fontes/fontes.json` | GPL-3.0 | lemas, categorías, flexión e conxugación |
| Thesaurus do VOLGa (Miguel Solla, 2010; extensión de LibreOffice de Trasno) | GPL-3.0 | sinónimos |
| [Open Multilingual Wordnet 1.4](https://github.com/omwn/omw-data): Galnet (MCR), omw-en, omw-es, omw-pt | CC BY 3.0 / WordNet License | sentidos, definicións en inglés, equivalentes |
| [Apertium](https://github.com/apertium) es-gl, spa-glg, pt-gl, en-gl | GPL-2.0 | traducións |
| [Apertium glg](https://github.com/apertium/apertium-glg) (monolingüe galego) | GPL-2.0 | capa `apertium`: léxico con flexión |
| Vocabularios terminolóxicos en PDF (USC, UDC, UVigo, Termigal/CIRP, RAG, Realiter; lista en `fontes/fontes.json`) | dereitos dos seus autores e editores; só se toman os termos, non as definicións | capa `vocabularios` |
| [ParlaMint-ES-GA](https://github.com/ILG-USC/ParlaMint-ES-GA) (actas do Parlamento de Galicia) | CC BY 4.0 | atestación do léxico administrativo engadido a man (non se copia texto) |
| [Wiktionary galego](https://gl.wiktionary.org/) e [inglés](https://en.wiktionary.org/) (vía kaikki.org) | CC BY-SA 4.0 | definicións, exemplos, sinónimos por acepción |
| `hyph_gl.dic` (extensión de LibreOffice de Trasno) | GPL-3.0 | separación silábica |
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles 2018) | CC BY-SA 4.0 | frecuencias |
| Revisión manual | GPL-3.0 | correccións segundo as *Normas ortográficas e morfolóxicas do idioma galego* (RAG/ILG) |
| [datasets/world-cities](https://github.com/datasets/world-cities) (GeoNames cities15000) | CC BY 4.0 | capa `cidades`: cidades do mundo |
| [Municipios de España](https://github.com/codeforspain/ds-organizacion-administrativa) (INE) | datos públicos do INE | capa `cidades` |
| [Freguesías de Portugal](https://github.com/pearlsofportugal/mvp-backend) (CAOP, DICOFRE) | datos oficiais (dados.gov.pt) | capa `cidades` |
| [openfootball/clubs](https://github.com/openfootball/clubs) | CC0 | capa `clubs`: nomes dos clubs de fútbol |
| [damegender](https://github.com/davidam/damegender) (ONS, Census, Destatis, INSEE, INE-PT, Idescat) e [SSA baby names](https://github.com/hadley/data-baby-names) | GPL-3.0; dominio público | capa `nomes-outras-linguas` |
| Engadidos a man (`fontes/engadidos/*.dic`) | GPL-3.0 | nomes propios e siglas que faltan nas fontes: tecnoloxía, marcas, entidades, clubs, capitais, persoas coñecidas, nomes doutras linguas |

Todo o proxecto (datos e código) publícase baixo a **GPL-3.0 ou posterior**
(`LICENSE`).

## Como contribuír

- **Corrixir unha conxugación**: engade a cela en `datos/correccions/conxugacions.json`
  cunha `nota`, executa `ferramentas/importar.py` e engade o verbo ás táboas de
  referencia de `probas/test_conxugacions.py`.
- **Revisar contra a RAG**: compara a táboa dun verbo co conxugador da RAG; se
  coincide, engádea ás probas de referencia para que quede protexida.
- **Engadir un nome propio ou unha sigla** que falta (unha empresa, unha cidade, unha
  persoa): unha liña en `fontes/engadidos/<capa>.dic` (`Nome po:nome_propio  # nota`;
  nos nomes compostos, cada palabra na súa liña con `is:ngrama_Nome_Completo`; `/999`
  se só vale coa súa grafía, como *iOS*), executa `ferramentas/capas.py <capa>` e revisa
  o cambio en `datos/capas/`. As palabras comúns non van aí: o núcleo é só da RAG.

## Folla de ruta

- [ ] Comunicar á RAG os erros do conxugador recollidos en `docs/rag/excluidos.json`.
- [ ] Repetir a comparación co conxugador da RAG de cando en vez (as táboas descárganse á caché; `--forzar` non existe aínda: bórrese `fontes/cache/rag/`).
- [ ] Ampliar as formas con enclíticos atestadas cun corpus maior.
- [ ] Revisar unha mostra das formas sistemáticas con enclíticos contra a RAG.
- [x] Probar `apple/Galego.apple` nun Mac (macOS 27).
- [ ] Probar o StarDict nunha app de iOS.
- [x] Xerar o `.dict` do teclado.
- [ ] Probar `teclado/main_gl.dict` en HeliBoard nun dispositivo.
- [ ] Probar o dicionario Kobo nun dispositivo.
- [ ] Comunicar a Proxecto Trasno os erros atopados (borrador en `docs/informe-trasno.md`).
