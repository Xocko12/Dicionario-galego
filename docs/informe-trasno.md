# Erros atopados nas regras de conxugación de hunspell-gl

*Borrador de incidencia para https://gitlab.com/trasno/hunspell-gl/-/issues.
Referencias de liña sobre `src/norma/xeral.aff` no commit `2c533b37` (2026-11-02).*

---

Ola,

Estamos a construír un catálogo aberto do léxico galego con flexión e conxugación
completas ([Dicionario galego aberto](https://github.com/Xocko12/Dicionario-galego),
GPL-3.0) a partir dos módulos `rag/gl` e `rag/volga` de hunspell-gl, e ao expandir
*todas* as formas que xeran as regras de `norma/xeral.aff` (non só comprobar
palabras soltas) atopamos unha serie de erros. Detallámolos por familias, coa
regra ou entrada responsable e a forma correcta segundo as *Normas ortográficas e
morfolóxicas* e o conxugador da RAG. Se preferides unha incidencia por punto,
dividímola sen problema.

## 1. Presente de subxuntivo P6 dos verbos en *-guer*

Xérase **ergugan, tangugan, abrangugan** en lugar de **ergan, tangan, abrangan**.
A regra quita `er` en vez de `guer`:

```
3711: SFX 310 er gan guer   → SFX 310 guer gan guer
```

Igual nas liñas 4314 (360), 4611 (410), 5214 (460), 5436 (470), 5570 (510) e 6173 (560).
Afecta a *erguer, soerguer, tanguer, atanguer, abranguer*.

## 2. Presente de subxuntivo P1/P3 de *ler* e *crer*

A regra xenérica de *-er* aplícase a *ler, crer, reler, descrer, trasler* e dá
**la, las, lan / cra, cras, cran** en vez de **lea, leas, lean / crea, creas, crean**:

```
3667: SFX 310 er a [^cuaos]er . is:subxuntivo presente P1 / P3
4567: SFX 410 er a [^cuaos]er
```

(e as regras irmás de P2, P4, P5 e P6). Faría falta excluír *ler/crer* da condición
e darlles regras propias con *-ea*.

## 3. Imperativo P2 dos verbos con alternancia vocálica

O imperativo P2 coincide coa P3 do presente (*dorme, sobe, segue*), pero a regra
de imperativo aplícase á raíz con *u/i*:

```
6802: SFX 614 ir e [^cu]ir . is:imperativo P2     → durme, sube, cuspe, fuxe, sacude...
7927: SFX 714 ir e [^cu]ir
```

e a raíz alternativa `siguir/666,623,723` dá **sigue** (correcto: **segue**).
Verbos afectados (módulo `rag/gl`): *acudir, bulir, conseguir, consentir, cubrir,
cuspir, descubrir, durmir, ferir, fuxir, lucir, mentir, mulir, perseguir, presentir,
proseguir, sacudir, seguir, sentir, servir, subir, sufrir, ulir, urdir, xurdir*.
Tamén *vir* e compostos: regra 640 dá **vien, convien, intervien, provien**
(correcto: **ven, convén, intervén, provén**).

## 4. Verbos irregulares con paradigma incompleto ou con formas falsas

- **ser**: *é* e *son* só están como anacos de n-gramas, non como formas do verbo.
  A regra xenérica 326 dá **sa, sas, san** no presente de subxuntivo (correcto só
  *sexa*, da raíz `sexer`), e a raíz `eser` coa regra 322 dá **eson**. Falta o
  imperativo **sé**.
- **ir**: falta o copretérito **ía, ías, ía, iamos, iades, ían**. A entrada
  `ír/630,730,830` (sen NEEDAFFIX) aplica todo o paradigma á raíz con til e xera
  **íraa, íreiche, írana, írasllo…** (correcto: *iraa, ireiche, irana, irasllo*).
- **dicir** e compostos: as regras 638/639 (raíz `dixer`) etiquetan **dixera,
  dixeras…** como `pospretérito`; é o antepretérito. O participio **dito** non
  forma parte do paradigma.
- **pór**: só ten os flags 350/450/550; faltan presente (*poño, pos, pon…*),
  pretérito (*puxen…*), subxuntivo (*poña…*) e participio (*posto*).
- **vir**: a raíz `viñer` coa regra 643 dá **vín** con til (correcto *vin*).
- **rir**: falta o presente P6 **rin**.
- **desoír**: a raíz alternativa `desordir` xera **desorde** como presente P3.
- **prover** / **desprover**: o pretérito queda incompleto e xéranse as variantes
  **provo, proves, prove** (segundo a RAG: *provexo, provés, prové; provín,
  proviches, proveu…; provido/provisto*).

## 5. Acentuación das formas con pronomes enclíticos

Comprobamos a acentuación de ~785 000 formas con enclíticos cunha implementación
independente das regras das Normas: coincide con hunspell-gl no 99,93 %. As
discrepancias agrúpanse así (lista completa, 272 formas, en
`encliticos-corrixidos.tsv`):

| Xerado | Correcto | Regra / causa |
|---|---|---|
| **vaiache, vaiase, vaiana** | váiache, váiase, váiana | raíz `vair`, regra 633 + 110/114: falta o til de esdrúxula (*vai-a-che*) |
| **cainnos, cainvos, doinnos** | caínnos, caínvos, doínnos | regra 411 + 120: pérdese o til do hiato de *caín, doín* |
| **ria, rias, rio** | ría, rías, río | regra 603 + 100: *ri* + *a* fai hiato |
| **estásme, estáslle, estásnos** | estasme, estaslle, estasnos | 2579: `SFX 205 ar ás/100,112,113`; o til só é correcto co enclítico polisílabo (113: *estásllela*), non co monosílabo (112) |
| **estívela, estíverme, déla, dérlle** | estivela, estiverme, dela, derlle | 2691 `íver/666,100,110,111,114,115` e 2693 `ér/…`: igual, o til só vale para 111/115 (*estivérvola*) |
| **dígamolo, dígadesche** | digámolo, digádesche | 7046-9250: `icir ígamos/…`, `icir ígades/…` → `igámos`, `igádes` |
| **íraa, íreiche, írana** | iraa, ireiche, irana | entrada `ír/630,730,830` (ver punto 4) |
| **érádela, érádesme, háánllelo** | erádela, erádesme, (non existe) | raíces con til (`érer`, `háber`) + sufixo con til: dúas vogais con til nunha palabra |

Os tiles diacríticos (*dáme, éche, vénme, pórlle*) consérvanse ben.

## Método

Expandimos cada entrada dos módulos `rag/gl` e `rag/volga` con todas as súas
regras (lector propio de `.aff/.dic`, comprobado con spylls), construímos a táboa
de cada verbo a partir das etiquetas `is:` e comparamos cada cela con patróns
xerais (subxuntivo desde a P1 do presente, P6 = P3 + *n*, imperativo P2 = presente
P3, etc.) e cunha acentuación independente. O código e as táboas de referencia
están no repositorio indicado; se vos é útil, podemos achegar un *merge request*
para os puntos 1, 2 e 5 (son cambios mecánicos nas regras).

Grazas polo traballo no corrector.
