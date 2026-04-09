# Claude Code AIFlow Pipeline — Konfiguracis es Fejlesztesi Keretrendszer

> **Verzio:** 1.0 | **Datum:** 2026-04-05
> **Cel:** Professzionalis, szabalyozott Claude Code fejlesztesi kornyezet kialakitasa tetszoleges projekthez.
> **Forrasok:** Anthropic hivatalos dokumentacio, kozossegi best practice-ek (84 dokumentalt minta).

---

## 1. Alapelvek

A Claude Code ot egymasra epulo alrendszerbol all. Az alabbi harom alapelv hatarozza meg a sikerességet:

**Kontextus-menedzsment a legfontosabb.** A leggyakoribb hibamod a kontextus degradacio — amikor Claude "elfelejti" a korabbi utasitasokat, mert a kontextusablak tulterhelodik. Minden konfiguracios dontesnek az a celja, hogy a kontextus tiszta es fokuszalt maradjon.

**Tervezes az implementacio elott nem opcionalis.** Production kod strukturalt gondolkodast, validalast es dokumentaciot igenyel. Hasznalj Planning Mode-ot, irott terveket es architektura review-kat mielott barmit kodolnal.

**Egyszeruseg felulmulja a komplexitast.** Egyszeru vezerlesi hurkok felulteljesitik a multi-agent rendszereket. Alacsony szintu eszkozok (Bash, Read, Edit) plusz szelektiv magas szintu absztrakciok hatekonyabbak, mint nehez RAG vagy komplex keretrendszerek.

---

## 2. Architektura — Az ot reteg

```
+-------------------------------------------------------------+
|  1. CLAUDE.md              — MINDIG AKTIV kontextus          |
|     Stack, konvenciok, build/test/lint, projekt terkep        |
|     Max ~100-150 sajat instrukció (a rendszer ~50-et foglal)  |
+-------------------------------------------------------------+
|  2. HOOKS                  — GARANTALT vegrehajtas            |
|     Lint/format/typecheck PostToolUse-ra                      |
|     Vedett fajlok deny PreToolUse-ra                          |
|     Teszt validalas Stop-ra (agent hook)                      |
+-------------------------------------------------------------+
|  3. SKILLS                 — ON-DEMAND szaktudas              |
|     Domain-specifikus workflow-ok, sablonok, referenciak      |
|     Automatikus betoltes relevancia alapjan VAGY /invoke      |
+-------------------------------------------------------------+
|  4. COMMANDS               — EXPLICIT, ismetelheto triggerek  |
|     Pipeline lepesek, feature ciklusok, review folyamatok     |
|     $ARGUMENTS tamogatas, subagent orchestracio               |
+-------------------------------------------------------------+
|  5. SUBAGENTS              — IZOLALT specialistak             |
|     Sajat kontextus, fokuszalt feladat, tiszta visszajelzes   |
|     Security reviewer, QA tester, architect, explorer         |
+-------------------------------------------------------------+
```

**Dontesi matrix — melyiket hasznald:**

| Szituacio | Eszkoz | Indoklas |
|-----------|--------|----------|
| Mindig igaz projekt szabaly | CLAUDE.md | Minden session-ben kell |
| Mindig le KELL futnia, elfelejtes nem opcio | Hook | Determinisztikus, nem fugg az LLM-tol |
| Domain-specifikus tudas, nem mindig kell | Skill | On-demand betoltes, nem terheli a kontextust |
| Explicit, manualis terminal trigger | Command | /parancs autocomplete, ismetelheto |
| Komplex feladat izolalt kontextusban | Subagent | Sajat kontextusablak, tiszta osszefoglalo |

---

## 3. CLAUDE.md — Reszletes utmutato

### 3.1. Elhelyezesi hierarchia

| Helyszin | Hatokor | Git-be kerul? |
|----------|---------|---------------|
| `~/.claude/CLAUDE.md` | Globalis, minden projekt | Nem (szemelyes) |
| `./CLAUDE.md` | Projekt gyoker, csapat szintu | **Igen** |
| `./CLAUDE.local.md` | Projekt, szemelyes feluliras | Nem (.gitignore) |
| `./packages/foo/CLAUDE.md` | Alkonyvtar (monorepo) | Igen |
| Szulo konyvtarak | Monorepo gyoker + al-CLAUDE.md-k | Igen |

Claude automatikusan osszefuzi a hierarchia relevans elemeit. Gyermek konyvtarak CLAUDE.md-jeit on-demand tolti be, amikor ott dolgozik.

### 3.2. Instrukció-koltsegvetes

A frontier thinking LLM-ek kb. **150-200 instrukciót** tudnak konzisztensen kovetni. A Claude Code sajat rendszerpromptja **~50 instrukciót** foglal el. Ez azt jelenti:

- **Te maximum ~100-150 sajat instrukciót** adhatsz meg mielott a kovetes minosege degradalodik
- Ahogy no az instrukciok szama, a kovetesi minoseg **egyenletesen csokken** — nem az ujabbakat hagyja figyelmen kivul, hanem az osszeset kezdi kevesbe kovetni
- Az LLM a prompt **elejet es veget** priorizalja (CLAUDE.md = eleje, legutóbbi user uzenet = vege)

### 3.3. A harom piller: MIT, MIERT, HOGYAN

**MIT** — Tech stack, projekt struktura, codebase terkep. Monorepo eseten kulonosen fontos: mi hol van, mi mire valo.

**MIERT** — A projekt celja, az egyes reszek funkcioja, az architekturalis dontesek indoklasai.

**HOGYAN** — Parancsok, workflow szabalyok, kod stilus. De: **ne probald meg az osszes lehetseges parancsot beleirni** — ez szuboptimalis eredmenyt ad.

### 3.4. Sablon

```markdown
# [Projekt neve]

## Struktura
[Monorepo/repo leiras: apps/, packages/, shared/ stb.]
[Tech stack: framework, UI lib, state mgmt, auth, DB]

## Build & Test
- `[build parancs]` — build
- `[test parancs --filter=<csomag>]` — MINDIG egyedi tesztet futtass
- `[typecheck parancs]` — kodvaltozas utan KOTELEZO

## Kod konvenciok
- [Import stilus, pl. ES modules, destructured imports]
- [Naming: camelCase, PascalCase komponensekre stb.]
- [Tiltasok + ALTERNATIVAK: "Ne hasznalj X-et; hasznald Y-t helyette"]

## Git workflow
- [Branch naming: feature/*, fix/*, stb.]
- [Commit formatum: conventional commits]
- [PR flow: ki review-zza, mi kell merge-hoz]

## FONTOS
- Compaction eseten ORIZD MEG: modositott fajlok listaja + teszt statusz
- Erzekeny adatokat (.env, kulcsok, credentials) SOHA ne commitolj
- [Egyeb kritikus szabaly hangsullyozassal: IMPORTANT / YOU MUST]

## Referenciak
- Komplex domain logikahoz lasd: docs/architecture.md
- API specifikaciohoz lasd: docs/api-spec.md
```

### 3.5. Kerulendo mintak (anti-patterns)

| Rossz | Jo | Miert |
|-------|-----|-------|
| `@docs/full-api-reference.md` | "API referenciahoz lasd: `docs/api-reference.md`" | Az @ az egesz fajlt beagyazza minden futasnal |
| "Soha ne hasznald a `--force` flaget" | "Soha ne hasznald a `--force`-t; hasznald a `--force-with-lease`-t" | Tiltas alternativa nelkul = agent elakad |
| 500 soros atfogo kezikonyv | 80-120 sor fokuszalt instrukciok | Tul hosszu = minden instrukció gyengul |
| Elmeleti best practice-ek | Ami nelkul Claude TENYLEG hibazna | Felesleges instrukció = zaj |

### 3.6. Importalas szintaxis

```markdown
## Referenciak
Lasd: @README.md a projekt attekinteshez
Lasd: @package.json az elerheto npm parancsokhoz
- Git workflow: @docs/git-instructions.md
- Szemelyes felulirasok: @~/.claude/my-project-instructions.md
```

> **Szabaly:** Csak akkor hasznalj @-importot, ha a fajl rovid es MINDIG relevans. Hosszu vagy ritkan szukseges fajlokra inkabb utvonal-hivatkozast adj meg szoveges formaban.

---

## 4. HOOKS — Reszletes utmutato

### 4.1. Alapelv

A CLAUDE.md instrukciok **tanacsado jelleguek** — a kontextus telitodesevsll elfelejtodhetnek. A hook-ok **determinisztikusak** — MINDIG lefutnak, az LLM dontésetol fuggetlenul. Barmit, aminek minden esetben, kivetel nelkul meg kell tortennie, hook-kent kell implementalni.

### 4.2. Hook esemenyek

| Esemeny | Mikor fut | Matcher? | Tipikus hasznalat |
|---------|-----------|----------|-------------------|
| `PreToolUse` | Eszkozhasznalat ELOTT | Igen | Fajlvedelem, parancs-blokkolas |
| `PostToolUse` | Eszkozhasznalat UTAN | Igen | Lint, format, typecheck |
| `UserPromptSubmit` | Prompt bekuldesekor | Nem | Input validacio, prompt transzformacio |
| `Stop` | Claude valasza vegen | Nem | Teszt futtatas, osszefoglalo |
| `SubagentStart` | Subagent inditasakor | Nem | Logolas, eroforras-allokacio |
| `SubagentStop` | Subagent leallasakor | Nem | Eredmeny routing, cleanup |
| `TaskCompleted` | Feladat befejezesekor | Nem | Ertesites, dashboard frissites |
| `TeammateIdle` | Teammate agent idle-ba megy | Nem | Munkaelosztas multi-agent setupban |
| `SessionStart` | Session inditasakor | Nem | Kornyezet-ellenorzes |
| `SessionEnd` | Session vegen | Nem | Cleanup, logolas |
| `ConfigChange` | Konfig fajl modosul | Nem | Konfig validacio |
| `WorktreeCreate` | Git worktree letrejon | Nem | Worktree setup |
| `WorktreeRemove` | Git worktree torlodik | Nem | Worktree cleanup |

### 4.3. Hook tipusok

| Tipus | Leiras | Timeout | Mikor hasznald |
|-------|--------|---------|----------------|
| `command` | Shell parancs futtatasa | 60s | Lint, format, egyszeru validacio |
| `prompt` | Egyetlen LLM hivas | 30s | Ha a hook input adataibol dontes hozhato |
| `agent` | Subagent teljes eszkozkeeszlettel | 60s (max 50 turn) | Ha fajlokat kell vizsgalni vagy parancsot futtatni |
| `http` | Webhook hivas | 30s | Kulso rendszer integracio |

### 4.4. Konfiguracio — `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write(*.ts)",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write $file && npx eslint --fix $file"
          }
        ]
      },
      {
        "matcher": "Write(*.py)",
        "hooks": [
          {
            "type": "command",
            "command": "python -m black $file && python -m ruff check --fix $file"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write(.env*)",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"decision\": \"deny\", \"reason\": \"Vedett fajl: .env modositasa tiltott\"}'"
          }
        ]
      },
      {
        "matcher": "Bash(rm -rf*)",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"decision\": \"deny\", \"reason\": \"Destruktiv parancs blokkolva\"}'"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Ellenorizd, hogy az osszes erintett unit teszt lefut-e. Futtasd a teszteket es foglald ossze az eredmenyt. $ARGUMENTS",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

### 4.5. Dontesi logika (PreToolUse)

A hook stdout-ra JSON-t ad vissza:

| Valasz | Hatas |
|--------|-------|
| `{"decision": "allow"}` | Atugorja az interaktiv engedelykerest (de deny szabalyok feluliijak!) |
| `{"decision": "deny", "reason": "..."}` | Blokkolja a muveletet, okot kuld Claude-nak |
| `{"decision": "ask"}` | Normal engedelykeres a felhasznalotol |

> **FONTOS:** Az "allow" NEM irja felul a deny szabalyokat. Ha egy deny szabaly illeszkedik, a hivas akkor is blokkolva lesz, meg ha a hook "allow"-t ad is vissza.

### 4.6. Hook-ok letrehozasa Claude-dal

Megkerheted Claude Code-ot, hogy irjon hook-okat:
- "Irj egy hook-ot, ami minden fajl szerkesztes utan eslint-et futtat"
- "Irj egy hook-ot, ami blokkolja az irast a migrations mappaban"
- Hasznald az interaktiv `/hooks` parancsot a hook-ok menubol konfiguralaasahoz

---

## 5. SKILLS — Reszletes utmutato

### 5.1. Alapelv

A skill-ek markdown fajlok, amelyek kiterjesztik Claude tudasat. A CLAUDE.md-vel ellentetben **nem minden session-ben toltodnek be** — csak akkor, ha Claude relevansnak iteli oket, vagy ha `/skill-neve` formaban explicit meghivod. Ezzel a kontextus tiszta marad.

### 5.2. Konyvtarstruktura

```
.claude/skills/
+-- auth-flow/
|   +-- SKILL.md              # Frontmatter + instrukciok
|   +-- templates/             # Kodsablonok
|   |   +-- auth-component.tsx
|   +-- scripts/               # Segedszkriptek
|       +-- check-auth.sh
+-- data-migration/
|   +-- SKILL.md
+-- deploy-staging/
|   +-- SKILL.md
+-- api-design/
    +-- SKILL.md
    +-- openapi-template.yaml
```

Globalis skill-ek: `~/.claude/skills/` — minden projektben elerhetok.
Projekt skill-ek: `.claude/skills/` — git-be commitolhatok, csapatszintu.

> **Precedencia:** Projekt szintu skill felulirrja a globalisat, ha azonos nevuek.

### 5.3. SKILL.md formatum

```markdown
---
name: auth-flow
description: >
  Autentikacio es authorizacio implementacio. Hasznald, amikor
  login/logout, token kezeles, session management, vagy
  jogosultsag-ellenorzes komponenseket kell fejleszteni.
allowed-tools: Read, Write, Grep, Glob, Bash
disable-model-invocation: false
---

# Auth Flow Implementacio

## Architektura
- Auth provider: [Keycloak/Auth0/Supabase/stb.]
- Token strategia: JWT access + refresh token
- Session store: [Redis/cookie/stb.]

## Fajl struktura
- `src/auth/` — auth modulok
- `src/middleware/auth.ts` — auth middleware
- `src/types/auth.ts` — TypeScript interfeszek

## Implementacios szabalyok
1. SOHA ne tarold a tokent localStorage-ban (XSS kockazat)
2. Refresh token MINDIG httpOnly cookie-ban
3. CSRF vedelem minden state-modosito kerésnel
4. Token lejarat ellenorzes middleware szinten

## Teszteles
pnpm test --filter=auth

## Referencia
Reszletes auth architektura: docs/auth-architecture.md
```

### 5.4. Frontmatter opciok

| Mezo | Tipus | Leiras |
|------|-------|--------|
| `name` | string | A /slash-command neve |
| `description` | string | Claude ez alapjan donti el, mikor toltse be automatikusan. Max 250 karakter jelenik meg. |
| `allowed-tools` | string | Eszkozok, amelyeket a skill engedelyez (Read, Write, Bash, Grep, Glob, WebFetch) |
| `disable-model-invocation` | bool | Ha true, Claude nem hivhatja meg automatikusan, csak explicit /invoke-kal |
| `model` | string | Specifikus modell a skill-hez (pl. claude-opus-4-6) |
| `argument-hint` | string | Hasznalati utmutato az argumentumokhoz |

### 5.5. Dinamikus tartalom a skill-ben

```markdown
---
name: project-status
description: Projekt statusz attekintes az aktualis git allapot alapjan
---

## Jelenlegi allapot
!`git log --oneline -10`

## Nyitott branch-ek
!`git branch -a --no-merged main`

## Utolso teszt eredmeny
!`cat test-results/latest.json 2>/dev/null || echo "Nincs korabbi teszt eredmeny"`
```

A `!command` szintaxis shell outputot injektal a promptba — Claude a meghivaskor lefuttatja, es csak az eredmenyt latja.

### 5.6. Skill description optimalizalas

A skill leirasok a kontextusba toltodnek, hogy Claude tudja, mi elerheto. A budget dinamikusan a kontextusablak **1%-a**, minimum 8000 karakter. Szabalyok:

- **Front-load:** A kulcs use case-t az elejere ird, mert 250 karakternel levag
- Ha sok skill-ed van es nem triggerelodnek: noveld a `SLASH_COMMAND_TOOL_CHAR_BUDGET` env variable-t
- Vagy roviditsd a leirasokat a forrasban

---

## 6. COMMANDS (Slash Commands) — Reszletes utmutato

### 6.1. Skill vs Command

A regi `.claude/commands/` es a `.claude/skills/` rendszer **osszeolvadt**. Mindket helyen levo fajlok ugyanazt a /slash-command interfeszt hozzak letre. A meglevo commands fajlok tovabbra is mukodnek.

A fo kulonbseg UX szinten:
- **Commands** = explicit, manualis trigger a terminalbol (/parancs + autocomplete)
- **Skills** = auto-discovered, Claude maga donti el mikor tolti be (+ manualisan is meghivhato)

Ha determinisztikus, ismetelheto terminal belepesi pontot akarsz -> **command formatum**
Ha gazdagabb workflow-t akarsz tamogato fajlokkal, amit Claude automatikusan is alkalmazhat -> **skill formatum**

### 6.2. Command elhelyezes

| Helyszin | Hatokor |
|----------|---------|
| `.claude/commands/` | Projekt szintu, git-be commitolhato |
| `~/.claude/commands/` | Globalis, szemelyes |
| `.claude/skills/*/SKILL.md` | Ugyanaz, de skill formatumban |

### 6.3. Pipeline command sablonok

#### /implement — Feature implementacio

```markdown
# .claude/commands/implement.md
---
description: Feature implementacio teljes ciklusban, fazisonkent
argument-hint: [feature leiras vagy SPEC.md hivatkozas]
allowed-tools: Read, Write, Bash, Grep, Glob
---

Implementald a kovetkezo feature-t fazisokra bontva:

## 1. Felfedezes
- Olvasd el a kapcsolodo kodot, SKILL.md fajlokat es dokumentaciot
- Azonositsd az erintett modulokat es fuggosegeket

## 2. Terv
- Keszits rovid implementacios tervet (max 15 sor)
- MUTASD MEG a tervet es VARD MEG a jovaahagyast mielott kodolnal

## 3. Implementacio
- Kovesd a CLAUDE.md konvenciokat
- Irj tipusos kodot, SOHA ne hasznalj any-t TypeScript-ben
- Egy fajl = egy felelosseg

## 4. Teszteles
- Irj unit teszteket MINDEN publikus funkciohoz
- Futtasd: [test parancs --filter=<erintett-csomag>]
- Futtasd: [typecheck parancs]
- MINDEN tesztnek PASSOLNIA kell mielott tovabblepnel

## 5. Osszefoglalo
- Listazd a modositott fajlokat
- Ird le, mit teszteltel es mi az eredmeny
- Jelezd, ha barmi nyitott kerdes maradt

Feature: $ARGUMENTS
```

#### /review — Kod review

```markdown
# .claude/commands/review.md
---
description: Kod review a valtozasokra, biztonsagi es minosegi szempontbol
argument-hint: [opcionalis: branch nev vagy fajl utvonal]
allowed-tools: Read, Grep, Glob, Bash
---

Vegezz alapos kod review-t az alabbi szempontok szerint:

## Vizsgalati szempontok
1. **Helyesseg:** Logikai hibak, edge case-ek, off-by-one hibak
2. **Biztonsag:** Injection, XSS, hardcoded secrets, OWASP Top 10
3. **Teljesitmeny:** N+1 query-k, felesleges renderek, memoria szivaargas
4. **Karbantarthatosag:** DRY, SOLID, ertheto naming, megfelelo absztrakcio
5. **Teszt lefedettseg:** Van-e teszt az uj/modositott logikahoz?

## Output formatum
Minden talaltatot kategorizalj:
- CRITICAL — azonnali javitas szukseges
- WARNING — javitas ajanlott merge elott
- SUGGESTION — opcionalis javitas

$ARGUMENTS
```

#### /spec — Specifikacio generalas interju modban

```markdown
# .claude/commands/spec.md
---
description: Interaktiv specifikacio generalas - Claude kerdez, te valaszolsz
argument-hint: [feature rovid leirasa]
---

Szeretnek egy reszletes specifikaciot kesziteni az alabbi feature-hoz.

FELADATOD:
1. Kerdezz meg reszletesen az AskUserQuestion eszkoyzzel
2. Kerdezz: technikai implementacio, edge case-ek, aggalyok, tradeoff-ok
3. NE kerdezz nyilvanvalo dolgokat
4. Folytasd az interjut amig MINDEN lenyeges reszlet tisztazva nincs
5. Ezutan ird meg a teljes specifikaciot SPEC.md-be

A specifikacio tartalmazza:
- Cel es kontextus
- Elfogadasi kriteriumok (acceptance criteria)
- Technikai megkozelites
- Edge case-ek es hibakezelees
- Nem-funkcionalis kovetelmenyek (teljesitmeny, biztonsag)
- Nyitott kerdesek (ha maradtak)

Feature: $ARGUMENTS
```

#### /create-pr — Pull Request keszites

```markdown
# .claude/commands/create-pr.md
---
description: PR letrehozas teljes workflow-val
allowed-tools: Read, Write, Bash, Grep, Glob
---

Keszits Pull Request-et a jelenlegi valtozasokhoz:

1. Ellenorizd, hogy minden teszt PASS
2. Futtass typecheck-et
3. Keszits conventional commit(okat) a valtozasokbol
4. Push-old a branch-et
5. Hozd letre a PR-t a kovetkezo strukturaval:
   - Cim: conventional commit formatumban
   - Leiras: Mi valtozott, miert, hogyan teszteltuk
   - Breaking changes jelolese ha relevans

$ARGUMENTS
```

### 6.4. Argumentumok

| Szintaxis | Leiras |
|-----------|--------|
| `$ARGUMENTS` | Az osszes argumentum egy stringkent |
| `$1`, `$2`, ... | Pozicionals argumentumok |

Pelda: `/implement Add dark mode support to the settings page`
-> `$ARGUMENTS` = "Add dark mode support to the settings page"

---

## 7. SUBAGENTS — Reszletes utmutato

### 7.1. Alapelv

A subagent-ek izolalt kontextusablakban futo Claude peldanyok, amelyek egy specifikus feladatra fokuszalnak. A fo elonyok:

- **Kontextus izolacio:** A "piszkos munka" (teszteles, nagy diffek, iterativ hibakereses) nem szennyezi a fo kontextust
- **Specializacio:** Sajat instrukciokeszlet, modell, eszkozok
- **Tiszta visszajelzes:** Osszefoglalot adnak vissza az orchestratornak

### 7.2. Subagent definicio

Subagent-ek helye: `.claude/agents/`

```markdown
# .claude/agents/security-reviewer.md
---
name: security-reviewer
description: Biztonsagi audit a kodbazison
model: claude-opus-4-6
allowed-tools: Read, Grep, Glob
---

Te egy senior biztonsagi auditor vagy. Feladatod:

## Vizsgalati teruletek
- SQL injection es NoSQL injection kockazatok
- XSS (stored, reflected, DOM-based) sebezhetosegek
- Hardcoded credentials, API kulcsok, tokenek
- CSRF vedelem hianya
- Erzekeny adatok naplozasa (PII, jelszavak, tokenek)
- Dependency sebezhetosegek (ismert CVE-k)
- OWASP Top 10 megfelelesseg

## Output formatum
Strukturalt jelentes kategoriakban:
- CRITICAL — azonnali javitas, deploy blokkolo
- HIGH — javitas szukseges merge elott
- MEDIUM — javitas ajanlott a kovetkezo sprintben
- LOW — ismert kockazat, elfogadhato

Minden talalathoz: fajl, sor, leiras, javitasi javaslat.
```

```markdown
# .claude/agents/qa-tester.md
---
name: qa-tester
description: QA teszt futtatas es validalas
allowed-tools: Read, Bash, Grep, Glob
---

Te egy QA mernok vagy. Feladatod:

1. Azonositsd az erintett modulokat a legutobbi valtozasokbol
2. Futtasd az erintett teszteket
3. Ha barmelyik FAIL: elemezd a hibat es javasold a javitast
4. Ellenorizd a teszt lefedettseeget az uj kodra
5. Adj osszefoglalot: PASS/FAIL + reszletek
```

```markdown
# .claude/agents/architect.md
---
name: architect
description: Architektura review es terv validalas
model: claude-opus-4-6
allowed-tools: Read, Grep, Glob
---

Te egy senior szoftverarchitekt vagy. Feladatod:

Vizsgald meg a javasolt tervet/implementaciot:
- Illeszkedik-e a meglevo architektturahoz?
- Vannak-e skalazhatosagi aggalyok?
- Megfelelo-e a separation of concerns?
- Van-e felesleges komplexitas, amit egyszerusiteni lehetne?
- Milyen technikai adossagot teremt?

Adj "Go / No-Go" dontest indoklassal.
```

### 7.3. Beepitett subagent-ek

| Subagent | Celja |
|----------|-------|
| `Explore` | Codebase felfedezes anelkul, hogy a fo kontextust terhelne |
| `Plan` | Tervezes es architektura |
| Altalanos celu | Default subagent, ha nem adsz meg specifikusat |

### 7.4. Context forking minta

A subagent-ek (kulonosen az implementer es QA) **forkolt kontextusban** futnak. Ez azt jelenti, hogy az osszes "piszkos munka" — npm test, hatalmas diffek, iterativ hibakereses �� izolaltan tortenik, majd **tiszta osszefoglalo** kerul vissza az orchestratorhoz.

### 7.5. Multi-session minta

A leghatekonyabb professzionalis workflow szetvalasztja az irast a review-tol:

1. **Session A** — Specifikacio: `/spec [feature]` -> interju -> SPEC.md
2. **Session B** (tiszta kontextus) — Implementacio: `/implement @SPEC.md`
3. **Session C** (tiszta kontextus) — Review: `/review` — friss szemmel, nincs implementacios bias

> "Az elso Claude implementalja a feature-t, a masodik Claude review-zza friss kontextusbol, mint egy staff engineer. A reviewer nem ismeri az implementacio shortcut-jait es mindegyiket megkerdojelezi."

---

## 8. Komplett pipeline konfiguracio

### 8.1. Fajlstruktura

```
projekt-gyoker/
+-- CLAUDE.md                          # Projekt kontextus (git-ben)
+-- CLAUDE.local.md                    # Szemelyes felulirasok (.gitignore)
+-- .claude/
|   +-- settings.json                  # Hooks, permissions, model config
|   +-- settings.local.json            # Szemelyes settings (.gitignore)
|   +-- skills/
|   |   +-- auth-flow/
|   |   |   +-- SKILL.md
|   |   |   +-- templates/
|   |   +-- data-layer/
|   |   |   +-- SKILL.md
|   |   +-- deploy/
|   |   |   +-- SKILL.md
|   |   +-- api-design/
|   |       +-- SKILL.md
|   |       +-- openapi-template.yaml
|   +-- commands/
|   |   +-- implement.md
|   |   +-- review.md
|   |   +-- spec.md
|   |   +-- create-pr.md
|   |   +-- status.md
|   +-- agents/
|       +-- security-reviewer.md
|       +-- qa-tester.md
|       +-- architect.md
+-- docs/
|   +-- architecture.md                # Reszletes architektura (skill-bol hivatkozva)
|   +-- api-spec.md
|   +-- adr/                           # Architecture Decision Records
+-- ...
```

### 8.2. Settings.json teljes minta

```json
{
  "model": "claude-sonnet-4-6",
  "permissions": {
    "allowedTools": [
      "Read", "Write", "Bash(npm *)", "Bash(pnpm *)",
      "Bash(git *)", "Bash(npx prettier *)", "Bash(npx eslint *)"
    ],
    "deny": [
      "Read(./.env)", "Read(./.env.*)",
      "Write(./.env)", "Write(./.env.*)",
      "Write(./production.config.*)",
      "Bash(rm -rf *)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write(*.ts)",
        "hooks": [{
          "type": "command",
          "command": "npx prettier --write $file && npx eslint --fix $file"
        }]
      },
      {
        "matcher": "Write(*.tsx)",
        "hooks": [{
          "type": "command",
          "command": "npx prettier --write $file && npx eslint --fix $file"
        }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write(.env*)",
        "hooks": [{
          "type": "command",
          "command": "echo '{\"decision\": \"deny\", \"reason\": \"Vedett fajl: .env modositasa tiltott. Hasznalj environment variable-ket.\"}'"
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "agent",
          "prompt": "Ellenorizd, hogy az erintett tesztek lefutnak-e. Ha FAIL, jelezd a hibat. $ARGUMENTS",
          "timeout": 120
        }]
      }
    ]
  }
}
```

### 8.3. Kontextus-menedzsment szabalyok

| Szituacio | Teendo |
|-----------|--------|
| Uj feladat kezdese | `/clear` — tiszta kontextus |
| Kontextus 50%-nal | Manualis `/compact` fokusz instrukciokkal |
| Komplex kutatas szukseges | Subagent-re delegalas (ne a fo kontextusba) |
| Feature kesz, review kell | Uj session friss kontextussal |
| Claude ketszer+ javitva ugyanarra | `/clear` + jobb prompt > hosszu session javitasokkal |
| Compaction | CLAUDE.md-ben: "Compaction eseten ORIZD MEG: [lista]" |

### 8.4. Modell-strategia

| Feladat | Ajanlott modell | Indoklas |
|---------|----------------|----------|
| Komplex architektura, tervezes | Opus | Legjobb reasoning |
| Altalanos fejlesztes | Sonnet (default) | Legjobb ar/ertek |
| Gyors exploracio, egyszeru kerdesek | Haiku | Leggyorsabb, legolcsobb |
| Subagent: exploracio | Haiku/Sonnet | Token-takarekos |
| Subagent: biztonsagi audit | Opus | Kritikus minoseg |

---

## 9. Professzionalis fejlesztesi workflow

### 9.1. Napi rutin

```
1. Session inditas -> Claude beolvassa CLAUDE.md-t
2. /status -> projekt allapot attekintes (skill dinamikus git outputtal)
3. /spec [feature] -> specifikacio interju modban -> SPEC.md
4. /clear -> tiszta kontextus
5. /implement @SPEC.md -> implementacio fazisokban
6. Hook: PostToolUse -> automatikus lint/format
7. Hook: Stop -> automatikus teszt validacio
8. /clear -> tiszta kontextus
9. /review -> kod review friss szemmel
10. Security subagent -> biztonsagi audit
11. /create-pr -> PR keszites
```

### 9.2. Iteracio a konfiguracion

A CLAUDE.md, skill-ek es hook-ok **elo dokumentumok** — folyamatosan finomitandok:

1. **Megfigyeld, hol hibazik Claude** -> Adj hozza instrukciót a CLAUDE.md-hez VAGY hook-ot
2. **Ha valami mindig igaz de neha elfelejti** -> Hook-ka alakitsd at
3. **Ha a CLAUDE.md tul hosszu lett** -> Mozgasd a ritkan szukseges tudast skill-be
4. **Ha egy workflow-t tobbszor ismetlesz** -> Alakitsd command-da
5. **Ha egy feladat szennyezi a kontextust** -> Delegald subagent-re
6. **Rendszeres audit:** Kerdezd meg minden sornal: "Claude TENYLEG hibazna enelkul?" — ha nem, torold

### 9.3. Csapatszintu megosztas

| Fajl | Git-be? | Megosztas |
|------|---------|-----------|
| `CLAUDE.md` | Igen | Csapat — mindenki ugyanazt a kontextust kapja |
| `CLAUDE.local.md` | Nem | Szemelyes — .gitignore |
| `.claude/settings.json` | Igen | Csapat — egyseeges hook-ok es permissions |
| `.claude/settings.local.json` | Nem | Szemelyes — .gitignore |
| `.claude/skills/` | Igen | Csapat — kozos domain tudas |
| `.claude/commands/` | Igen | Csapat — kozos workflow-k |
| `.claude/agents/` | Igen | Csapat — kozos subagent-ek |
| `~/.claude/` | Nem | Szemelyes globalis — nem repo-specifikus |

---

## 10. Osszefoglalo — Gyors dontesi fa

```
Kerdes: "Ezt hova tegyem?"

Mindig igaz, univerzalis szabaly?
  IGEN -> CLAUDE.md

Mindig le kell futnia, elfelejtes nem opcio?
  IGEN -> HOOK

Domain-specifikus, csak neha kell?
  IGEN -> SKILL

Explicit terminal trigger, ismetelheto?
  IGEN -> COMMAND

Izolalt kontextus kell, ne szennyezze a fot?
  IGEN -> SUBAGENT

Szemelyes preferencia, nem csapat szabaly?
  IGEN -> CLAUDE.local.md vagy ~/.claude/
```

---

## Hivatkozasok

- **Anthropic hivatalos best practices:** https://code.claude.com/docs/en/best-practices
- **Skills dokumentacio:** https://code.claude.com/docs/en/skills
- **Hooks utmutato:** https://code.claude.com/docs/en/hooks-guide
- **CLAUDE.md utmutato (Anthropic blog):** https://claude.com/blog/using-claude-md-files
- **Kozossegi best practices (84 minta):** https://github.com/shanraisshan/claude-code-best-practice
- **Awesome Claude Code (skills, hooks, plugins):** https://github.com/hesreallyhim/awesome-claude-code
- **Plugins dokumentacio:** https://www.anthropic.com/news/claude-code-plugins
