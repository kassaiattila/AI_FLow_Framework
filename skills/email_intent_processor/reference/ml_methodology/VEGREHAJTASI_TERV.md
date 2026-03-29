# Végrehajtási Terv - Feldolgozott Tananyag

> Utolsó frissítés: 2026-03-27

---

## Aktuális Állapot

### Elkészült (Magyar verzió) - v2

| Elem | Darab | Sorok | Állapot |
|------|-------|-------|---------|
| Tematikus útmutatók (00-13) | 14 | ~12,888 | **KÉSZ** |
| Python kód példák | 12 | ~9,689 | **KÉSZ**, szintaxis OK |
| Forrásgyűjtemény | 1 | 148 | **KÉSZ** |
| PDF pótlás (01, 03, 04) | 3 útmutató | +587 sor | **KÉSZ** |
| Kimaradt transzkriptek (01_01, 01_02) | 2 | beépítve 01-be | **KÉSZ** |
| Vizuális verziók (01, 03, 04) | 3 | 2,667 sor, 59 kép | **KÉSZ** |
| Slide képek kinyerve | 73 PNG | 1920x1080 | **KÉSZ** |
| **7-8. heti útmutatók (10-13)** | **4** | **~3,145** | **KÉSZ** |
| **7-8. heti kód példák** | **4** | **~2,991** | **KÉSZ** |
| **Kereszthivatkozások frissítve** | **6 útmutató** | - | **KÉSZ** |

### Forrás Lefedettség

| Forrástípus | Összesen | Feldolgozva | Kimaradt |
|-------------|----------|-------------|----------|
| MD transzkriptek (0-6. hét) | 73 | 72 | 1 (`00_01` - kihagyva, felület használat) |
| MD transzkriptek (7-8. hét) | 23 | **23** | 0 |
| PDF prezentációk | 5 (+2 duplikát) | **5** | 0 |
| Jupyter notebookok | 6 | **6** | 0 |
| CSV adatfájlok | 5 | 0 (notebook részeként) | - |
| PDF slide képek | 73 PNG | 73 | 0 |
| 7. hét forráskód | 6 fájl + 3 notebook | **beépítve 10-be** | 0 |

---

## Hátralévő Feladatok - Teljes Lista

### ~~FELADAT 1: PDF Pótlás~~ [KÉSZ 2026-03-09]

Minden PDF beépítve + kimaradt transzkriptek pótolva. Eredmény:

| Útmutató | Növekedés |
|----------|-----------|
| 01_ml_alapfogalmak | 378 → 703 sor (+325) |
| 03_adatmegertes_es_eda | 652 → 740 sor (+88) |
| 04_adatelokeszites | 810 → 984 sor (+174) |

`2het_PPT (1).pdf` = duplikátum → kihagyva.

---

### ~~FELADAT 1b: Vizuális Verziók~~ [KÉSZ 2026-03-09]

PDF slide-ok képként kinyerve (73 PNG, 1920x1080) → `_kepek/` almappákba.
3 vizuális verzió készül, ami a meglévő útmutatót beágyazott slide képekkel egészíti ki.

**Struktúra**:
```
feldolgozott_tananyag/
├── _kepek/
│   ├── 01_basic_concepts/    (16 slide PNG)
│   ├── 02_tasks_of_ml/       (25 slide PNG)
│   ├── 03_data_understanding/ (10 slide PNG)
│   └── 04_data_preparation/   (22 slide PNG)
├── 01_ml_alapfogalmak_es_tipusok.md           (szöveges, PDF-ből is)
├── 01_ml_alapfogalmak_es_tipusok_VIZUALIS.md  (képekkel)
├── 03_adatmegertes_es_eda.md                  (szöveges)
├── 03_adatmegertes_es_eda_VIZUALIS.md         (képekkel)
├── 04_adatelokeszites_es_feature_engineering.md
└── 04_adatelokeszites_es_feature_engineering_VIZUALIS.md
```

**Elv**: A `_VIZUALIS.md` fájlok az eredeti útmutató tartalmát tartalmazzák, kiegészítve a releváns slide képekkel, magyar feliratokkal és képjegyzékkel. Csak érdemi diagramok/ábrák kerülnek be (címlapok, szöveges slide-ok kihagyva).

---

### ~~FELADAT 2: Új Heti Tananyagok Feldolgozása~~ [KÉSZ 2026-03-27]

A 7-8. hét anyaga feldolgozva. A kurzus 8 hetes, ezzel a teljes anyag lefedett.

#### Workflow Új Anyag Esetén

```
1. FORRÁS AZONOSÍTÁS
   ├── ls Tanayag/XX_het/ → új MD, PDF, IPYNB fájlok
   ├── Témakör meghatározása
   └── Döntés: meglévő útmutató bővítése VAGY új útmutató?

2. FELDOLGOZÁS (párhuzamos agent-ekkel)
   ├── Agent 1: MD transzkriptek + PDF → útmutató MD
   ├── Agent 2: Jupyter notebook → _kod_peldak/*.py
   └── Mindkettő a sablon szerint

3. KARBANTARTÁS
   ├── 00_attekintes frissítése (hivatkozások, táblázat, sorszámok)
   ├── Kereszthivatkozások más útmutatókban
   ├── hasznos_linkek.md bővítése
   └── py_compile ellenőrzés
```

#### Tényleges Feldolgozott Témák (7-8. hét)

| Hét | Téma | Útmutató | Kód fájl | Állapot |
|-----|------|----------|----------|---------|
| 7 | MLOps, DevOps, CI/CD, REST API, Deployment | `10_mlops_es_deployment.md` (978 sor) | `mlops_pipeline.py` (1513 sor) | **KÉSZ** |
| 8 | Anomália detekció (GMM, IF, self-supervised) | `11_anomalia_detektio.md` (606 sor) | `anomalia_detektio.py` (548 sor) | **KÉSZ** |
| 8 | Ajánlórendszerek (content, CF, association) | `12_ajanlorendszerek.md` (874 sor) | `ajanlorendszerek.py` (554 sor) | **KÉSZ** |
| 8 | Deep Learning alapok (perceptron, ANN, DL arch.) | `13_deep_learning_alapok.md` (687 sor) | `deep_learning_alapok.py` (376 sor) | **KÉSZ** |

#### Útmutató Sablon (Változatlan)

```markdown
# [Téma neve]

## Gyors Áttekintés
> 2-3 mondatos összefoglaló

## Kulcsfogalmak
- **Fogalom**: definíció

## Elmélet Tömören

## Gyakorlati Útmutató
### Mikor használd?
### Lépésről lépésre
### Kód példák

## Összehasonlító Táblázat (ahol releváns)
| Módszer | Előny | Hátrány | Mikor használd |

## Gyakori Hibák és Tippek

## Kapcsolódó Témák

## További Források
```

---

### FELADAT 3: Magyar Slide-ok / Prezentációs Anyagok

A meglévő magyar útmutatókból **Marp Markdown slide deck-ek** készítése, amelyek PDF-be és PPTX-be exportálhatók.

#### Kimeneti Struktúra

```
feldolgozott_tananyag/
└── _slides_HU/
    ├── 01_ml_alapfogalmak_slides.md
    ├── 02_fejlesztoi_kornyezet_slides.md
    ├── 03_adatmegertes_eda_slides.md
    ├── 04_adatelokeszites_slides.md
    ├── 05_felugyelt_tanulas_slides.md
    ├── 06_validacio_metrikak_slides.md
    ├── 07_hyperparameter_slides.md
    ├── 08_dimenziocsokkentes_slides.md
    └── 09_klaszterezes_slides.md
```

#### Slide Generálási Elvek

- Minden útmutatóból **15-25 slide**
- Marp-kompatibilis Markdown (`---` slide elválasztóval)
- Tartalom: kulcsdefiníciók, összehasonlító táblázatok, kód snippetek, döntési fák
- Vizuális: minimális szöveg slide-onként, táblázatok és kód blokkok
- Formátum:

```markdown
---
marp: true
theme: default
paginate: true
header: 'ML Engineering - [Téma]'
footer: 'Cubix EDU feldolgozott tananyag'
---

# Téma Címe

---

## Slide Cím

- Lényeg 1
- Lényeg 2

---
```

#### Végrehajtás
- 9 párhuzamos agent (témánként 1)
- Input: meglévő magyar útmutató MD
- Output: Marp slide deck MD
- Export: `npx @marp-team/marp-cli slide.md --pdf` vagy `--pptx`

---

### FELADAT 4: Angol Nyelvű Verzió (English Mutation)

A teljes anyag **natív angol** változatának elkészítése: útmutatók + kód + slide-ok.

#### Kimeneti Struktúra

```
feldolgozott_tananyag_EN/
├── 00_overview_and_navigation.md
├── 01_ml_fundamentals_and_types.md
├── 02_development_environment_and_pandas.md
├── 03_data_understanding_and_eda.md
├── 04_data_preparation_and_feature_engineering.md
├── 05_supervised_learning_algorithms.md
├── 06_model_validation_and_metrics.md
├── 07_hyperparameter_optimization.md
├── 08_dimensionality_reduction.md
├── 09_clustering.md
├── _code_examples/
│   ├── pandas_basics.py
│   ├── eda_examples.py
│   ├── data_preparation.py
│   ├── supervised_ml.py
│   ├── validation_metrics.py
│   ├── hyperparameter_optuna.py
│   ├── dimensionality_reduction.py
│   └── clustering.py
├── _slides/
│   ├── 01_ml_fundamentals_slides.md
│   ├── 02_dev_environment_slides.md
│   ├── 03_eda_slides.md
│   ├── 04_data_preparation_slides.md
│   ├── 05_supervised_learning_slides.md
│   ├── 06_validation_metrics_slides.md
│   ├── 07_hyperparameter_tuning_slides.md
│   ├── 08_dimensionality_reduction_slides.md
│   └── 09_clustering_slides.md
├── _presentations/
│   ├── *.pdf           (Marp PDF export)
│   └── *.pptx          (Marp PPTX export)
└── _resources/
    └── useful_links.md
```

#### Fordítási Elvek

**NEM szó szerinti fordítás**, hanem **natív angol újraírás**:

1. **Terminológia**: ML szakkifejezések angolul (amúgy is angol eredetűek)
2. **Kód kommentek**: Magyar → angol cserélés minden `.py` fájlban
3. **Példák**: Nemzetközi kontextusra adaptálás
4. **Stílus**: Technikai dokumentáció stílus (tömör, szakmai)
5. **Kiegészítés**: Kurzus-specifikus hivatkozások → általánosabb megfogalmazás
6. **Fájlnevek**: Magyar → angol (pl. `klaszterezes.py` → `clustering.py`)

#### Végrehajtási Sorrend

| Lépés | Feladat | Agent-ek |
|-------|---------|----------|
| 4.1 | Útmutatók angol újraírása (01-09) | 9 párhuzamos |
| 4.2 | Kód kommentek fordítása (8 fájl) | 8 párhuzamos |
| 4.3 | Angol slide deck-ek generálása (9 téma) | 9 párhuzamos |
| 4.4 | 00_overview + _resources fordítása | 1 agent |
| 4.5 | Kereszthivatkozások ellenőrzés | 1 agent |
| 4.6 | PDF/PPTX export (Marp CLI) | bash script |

#### Agent Prompt Sablon (Útmutató Fordítás)

```
Read the Hungarian guide at [path].
Rewrite it in native English (NOT machine translation).
- Keep the same structure and section headers (translated)
- ML terminology stays in English (already is)
- Translate table headers and content
- Update file references to English filenames
- Remove Cubix-specific references, make it general
Write to [EN path].
```

#### Agent Prompt Sablon (Kód Fordítás)

```
Read the Python file at [path].
Replace all Hungarian comments with English equivalents.
Keep the code logic identical.
Rename the file to English (e.g. klaszterezes.py → clustering.py).
Write to [EN path].
```

#### Agent Prompt Sablon (Slide Generálás)

```
Read the English guide at [EN path].
Create a Marp Markdown slide deck (15-25 slides).
Include: key definitions, comparison tables, code snippets, decision trees.
Format: marp: true, theme: default, paginate: true.
Write to [slides path].
```

---

### FELADAT 5: Minőségbiztosítás

#### Ellenőrzési Checklist (Minden Frissítés Után)

**Tartalom**:
- [ ] Minden forrás MD legalább egy útmutatóban felhasználva
- [ ] Minden PDF prezentáció tartalma beépítve
- [ ] Minden Jupyter notebook kódja kinyerve
- [ ] LIVE alkalmak Q&A beépítve releváns útmutatókba
- [ ] Útmutatók sablon-konformok

**Kód**:
- [ ] `_kod_peldak/*.py` szintaktikailag helyes (`py_compile`)
- [ ] Kód futtatható (sklearn datasets, nincs external dependency)
- [ ] Opcionális importok try/except-tel kezelve

**Hivatkozások**:
- [ ] `00_attekintes` minden útmutatóra hivatkozik
- [ ] Kereszthivatkozások működnek (relatív linkek)
- [ ] `hasznos_linkek.md` naprakész

**Angol verzió** (ha létezik):
- [ ] Angol verzió szinkronban a magyarral
- [ ] Slide deck-ek tartalmazzák a kulcs anyagokat
- [ ] PPTX/PDF exportok léteznek

#### Spot-Check Protokoll

Minden nagyobb frissítés után 2-3 útmutató ellenőrzése:
1. Tartalom **pontossága** (definíciók, képletek, kód)
2. Tartalom **teljessége** (nem maradt-e ki forrásanyag)
3. Kód **futtathatósága**
4. **Hivatkozások** működnek
5. **Konzisztencia** más útmutatókkal

---

## Végrehajtási Ütemterv

```
FELADAT 1: PDF Pótlás                    [████████████] KÉSZ
FELADAT 2: 7-8. hét feldolgozása         [████████████] KÉSZ (v2)
FELADAT 3: Magyar Slide-ok               [░░░░░░░░░░░░] Következő lépés
FELADAT 4: Angol Verzió                  [░░░░░░░░░░░░] Feladat 3 után
  4.1 Útmutatók fordítása                [░░░░░░░░░░░░]
  4.2 Kód kommentek fordítása            [░░░░░░░░░░░░]
  4.3 Angol slide-ok                     [░░░░░░░░░░░░]
  4.4-4.6 Finalizálás                    [░░░░░░░░░░░░]
FELADAT 5: QA                            [░░░░░░░░░░░░] Minden fázis után
```

### Javasolt Sorrend

| # | Feladat | Előfeltétel | Párhuzamosítható |
|---|---------|-------------|------------------|
| 1 | PDF pótlás befejezése | - | **KÉSZ** |
| 2 | 7-8. hét feldolgozása (v2) | - | **KÉSZ** (4 agent párhuzamosan) |
| 3 | Magyar slide-ok (14 téma) | Feladat 1+2 kész | Igen (14 agent) |
| 4.1 | Angol útmutatók | Feladat 1+2 kész | Igen (14 agent) |
| 4.2 | Angol kód | Feladat 4.1-gyel párhuzamosan | Igen (12 agent) |
| 4.3 | Angol slide-ok | Feladat 4.1 kész | Igen (9 agent) |
| 4.4 | Angol overview + resources | Feladat 4.1 kész | 1 agent |
| 4.5 | Angol hivatkozás-check | Feladat 4.1-4.4 kész | 1 agent |
| 4.6 | PDF/PPTX export | Feladat 3 + 4.3 kész | bash script |
| 5 | QA | Minden fázis után | 1-2 agent |

### Becsült Agent Használat

| Feladat | Agent-ek száma | Batch-ek |
|---------|---------------|----------|
| PDF pótlás | 3 | 1 (kész) |
| Magyar slide-ok | 9 | 1 |
| Angol útmutatók + kód | 17 (9+8) | 2 |
| Angol slide-ok | 9 | 1 |
| QA + finalizálás | 2-3 | 1 |
| **Összesen** | ~40 agent | ~6 batch |

---

## Parancs Referencia

### Következő Session Indítása

```
"Folytassuk a végrehajtási tervvel:
1. Ellenőrizd a PDF pótlás eredményét
2. Csináld meg a magyar slide-okat (FELADAT 3)
3. Indítsd el az angol fordítást (FELADAT 4)"
```

### Új Heti Anyag Feldolgozása

```
"Új anyag érkezett: Tanayag/XX_het/
1. Listázd az új fájlokat
2. Határozd meg melyik útmutatóhoz tartoznak
3. Dolgozd fel párhuzamos agent-ekkel
4. Frissítsd a 00_attekintes-t"
```

### Teljes Angol Verzió

```
"Készítsd el az angol verziót:
1. feldolgozott_tananyag_EN/ mappa létrehozása
2. 9 útmutató párhuzamos fordítása
3. 8 kód fájl komment fordítása
4. 9 slide deck generálása
5. Overview + resources
6. QA ellenőrzés"
```
