# RAG Chat Redesign — Profi Chat UX + LLM Selector

## Context

A jelenlegi `ChatPanel.tsx` (273 sor, egyetlen fájl) egy alapszintű chat UI. A felhasználó kéri:
- Klasszikus chat elrendezést (bal-rendezett, avatar, timestamp)
- Chat history mentést (localStorage)
- Profi görgetést (scroll-to-bottom gomb, ne zavarjon ha felfele görgetek)
- Prompt history (fel/le nyíl billentyű = előző/következő üzenet)
- Copy gomb az AI válaszoknál
- **ÚJ funkció:** LLM modell választó (gpt-4o, gpt-4o-mini, claude-sonnet, stb.)

A meglévő funkciók (collection selector, sources block, response time, feltöltés, progress bar) MARADNAK.

---

## 1. Fájlstruktúra: ChatPanel → könyvtár

A `ChatPanel.tsx`-et felváltja egy `ChatPanel/` könyvtár. Az import path (`../components-new/ChatPanel`) automatikusan resolve-ol `index.tsx`-re.

```
components-new/ChatPanel/
  index.tsx              — fő orchestrator (ChatPanel export)
  types.ts               — ChatMessage, props, AVAILABLE_MODELS
  ChatHeader.tsx         — collection + model selector + clear history
  MessageList.tsx        — scrollable lista + auto-scroll logika
  MessageBubble.tsx      — avatar, név, timestamp, tartalom, copy gomb
  SourcesBlock.tsx       — meglévő collapsible sources (áthelyezés)
  ChatInput.tsx          — textarea, auto-resize, shift+enter, history
  ScrollToBottom.tsx     — lebegő gomb ha felfele görgettünk
  useChatHistory.ts      — localStorage persistence per collection
  usePromptHistory.ts    — fel/le nyíl = előző promptok
```

**Törlendő:** `components-new/ChatPanel.tsx` (a könyvtár váltja fel)

---

## 2. Backend: model paraméter hozzáadása

### 2a. API — `src/aiflow/api/v1/rag_engine.py`

`QueryRequest`-hez (sor ~60):
```python
model: str | None = None  # override answer model
```

`QueryResponse`-hoz (sor ~65):
```python
model_used: str | None = None
```

`query_collection()` endpoint-ban (sor ~480): `model=request.model` átadás service-nek.

### 2b. Service — `src/aiflow/services/rag_engine/service.py`

`query()` metódus (sor 466) — új param:
```python
async def query(self, collection_id, question, role="expert", top_k=None, model=None):
```

Sor 549 — model override:
```python
answer_model = model or self._ext_config.default_answer_model
result = await self._model_client.generate(..., model=answer_model, ...)
```

`QueryResult`-hoz (sor 69):
```python
model_used: str = ""
```

Return-ben (sor 589): `model_used=answer_model`.

### 2c. Alembic migráció NEM KELL
A `rag_query_log` tábla nincs érintve (model nem kerül a logba most).

---

## 3. Frontend implementáció (lépésenként)

### 3a. types.ts

```typescript
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: { text: string; score: number; document_title?: string }[];
  responseTime?: number;
  timestamp: number;      // ÚJ: Date.now()
  model?: string;         // ÚJ: melyik LLM válaszolt
}

export const AVAILABLE_MODELS = [
  { id: "openai/gpt-4o", label: "GPT-4o" },
  { id: "openai/gpt-4o-mini", label: "GPT-4o Mini" },
  { id: "openai/gpt-4.1", label: "GPT-4.1" },
  { id: "openai/gpt-4.1-mini", label: "GPT-4.1 Mini" },
  { id: "anthropic/claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
  { id: "anthropic/claude-haiku-4-20250514", label: "Claude Haiku 4" },
] as const;
```

### 3b. useChatHistory.ts

- Key: `aiflow_chat_history_{collectionId}`
- Max 100 üzenet/collection (legrégebbi törlése)
- `addMessage()`, `clearHistory()` API
- Debounced localStorage write (500ms)

### 3c. usePromptHistory.ts

- Elkülött user promptok tömbje (max 50)
- `navigateUp()` / `navigateDown()` — index kezelés
- localStorage: `aiflow_chat_prompt_history`

### 3d. MessageBubble.tsx — klasszikus chat layout

```
[Avatar ikon] [Név] [HH:mm timestamp]     [Copy ikon hover-re]
[Tartalom - teljes szélesség]
[SourcesBlock — ha assistant és van source]
[1234ms | GPT-4o badge — ha assistant]
```

- **Mindkét oldal bal-rendezett** (nincs jobb-rendezés)
- User: person ikon + "You"/"Te"
- Assistant: sparkle ikon + "AI Assistant"/"AI Asszisztens"  
- Copy gomb: `navigator.clipboard.writeText()` + 2s "Copied!" feedback
- Hover csoport: `group` + `group-hover:opacity-100`

### 3e. ChatInput.tsx

- `<textarea rows={1}>` + auto-resize (`scrollHeight` alapján, max 200px)
- `Enter` = küldés, `Shift+Enter` = új sor
- `ArrowUp` kurzor 0-nál = előző prompt, `ArrowDown` végén = következő
- Send gomb jobb oldalon (meglévő stílus)

### 3f. Smart scroll

- `onScroll` listener a message container-en
- "At bottom" = `scrollTop + clientHeight >= scrollHeight - 40`
- Auto-scroll CSAK ha at bottom + új üzenet
- `ScrollToBottom` gomb: fix pozíció, lefelé nyíl, animált megjelenés

### 3g. ChatHeader.tsx

```
[Collection dropdown (ha !collectionId)]  [Model dropdown]  [Clear history gomb]
```

Model: localStorage `aiflow_chat_model`, default `openai/gpt-4o`

---

## 4. i18n kulcsok (ragChat.*)

| Kulcs | EN | HU |
|-------|----|----|
| model | Model | Modell |
| clearHistory | Clear history | Előzmény törlése |
| clearHistoryConfirm | Clear chat history? | Chat előzmény törlése? |
| copied | Copied! | Másolva! |
| you | You | Te |
| assistant | AI Assistant | AI Asszisztens |
| scrollToBottom | Scroll to bottom | Görgetés lefelé |

**Fájlok:** `aiflow-admin/src/locales/{en,hu}.json`

---

## 5. Érintett fájlok összefoglaló

| Fájl | Művelet |
|------|---------|
| `components-new/ChatPanel.tsx` | TÖRLÉS (könyvtár váltja fel) |
| `components-new/ChatPanel/index.tsx` | ÚJ — orchestrator |
| `components-new/ChatPanel/types.ts` | ÚJ — típusok + model lista |
| `components-new/ChatPanel/ChatHeader.tsx` | ÚJ — header |
| `components-new/ChatPanel/MessageList.tsx` | ÚJ — lista + scroll |
| `components-new/ChatPanel/MessageBubble.tsx` | ÚJ — üzenet renderelés |
| `components-new/ChatPanel/SourcesBlock.tsx` | ÁTHELYEZÉS ChatPanel.tsx-ből |
| `components-new/ChatPanel/ChatInput.tsx` | ÚJ — textarea + history |
| `components-new/ChatPanel/ScrollToBottom.tsx` | ÚJ — gomb |
| `components-new/ChatPanel/useChatHistory.ts` | ÚJ — hook |
| `components-new/ChatPanel/usePromptHistory.ts` | ÚJ — hook |
| `src/aiflow/api/v1/rag_engine.py` | MÓDOSÍTÁS — model param |
| `src/aiflow/services/rag_engine/service.py` | MÓDOSÍTÁS — model override |
| `src/locales/en.json` | MÓDOSÍTÁS — új kulcsok |
| `src/locales/hu.json` | MÓDOSÍTÁS — új kulcsok |
| `pages-new/Rag.tsx` | NEM VÁLTOZIK (import auto-resolve) |
| `pages-new/RagDetail.tsx` | NEM VÁLTOZIK (import auto-resolve) |

---

## 6. Implementációs sorrend

1. **Backend** — model param (rag_engine.py + service.py) — ez kell a frontend-nek
2. **types.ts + i18n** — alapok
3. **SourcesBlock.tsx** — áthelyezés (változatlan)
4. **useChatHistory + usePromptHistory** — hookok
5. **MessageBubble + ChatInput + ScrollToBottom** — UI komponensek
6. **ChatHeader + MessageList** — összerakás
7. **index.tsx** — orchestrator (fő ChatPanel)

---

## 7. Figma Design Alapok — Untitled UI Messaging Komponensek

### 7a. Felhasználható Untitled UI komponensek (Figma library)

**Messaging page** (`1251:12271`) — 10 child frame:
| Komponens | Figma variáns | Felhasználás |
|-----------|--------------|-------------|
| `Message` (Received) | Avatar + Name + Time + Bubble | Assistant üzenet renderelés |
| `Message` (Sent) | "You" + Time + Bubble (brand szín) | User üzenet renderelés |
| `Message` (Writing) | Avatar + három pont animáció | Loading/typing indikátor |
| `Message` (Attachment) | Fájl ikon + név + méret | Source attachment megjelenítés |
| `_Message reaction` | Emoji + count badge | Feedback gombok (👍👎) |
| `Slide out menu` | Header + Tabs + Messages + Input | Teljes chat panel struktúra |
| `Content divider` | "Today" dátum szeparátor | Nap-szeparátor üzenetek között |

**Egyéb felhasználható komponensek:**
| Komponens | Figma page | Felhasználás |
|-----------|-----------|-------------|
| `Avatars` (`18:1350`) | 18 variáns | User/AI avatar ikonok |
| `Badges` (`12:539`) | 8 variáns | Model badge, source score |
| `Inputs` (`85:1269`) | 14 variáns | Chat textarea |
| `Select` (`7684:90446`) | 10 variáns | Collection + Model dropdown |
| `Toggles` (`1102:4631`) | 7 variáns | Role selector toggle |
| `Tooltips` (`1052:485`) | 6 variáns | Copy "Copied!" tooltip |
| `Buttons` (`1:1183`) | 15 variáns | Send, Clear, New Chat gombok |

### 7b. Meglévő AIFlow RAG Chat Figma design (`11625:10532`)

Már van egy profi chat design! A struktúra:
```
RAG Chat page
├── Header: "RAG Chat" + "Collections" gomb + "New Chat" gomb
├── Controls Bar
│   ├── Collection Selector (dropdown)
│   └── Role Selector (Baseline / Mentor / Expert pill-ek)
├── Chat Wrapper (Messages)
│   ├── Empty State: hint text + 3 preset kérdés kártya
│   ├── User Msg: jobb oldali brand-szín buborék
│   └── Assistant Response Card
│       ├── Answer Text (bal oldali szürke kártya)
│       ├── Sources: chip-ek ([1] ASZF 4.2.1, [2] ASZF 4.2.3)
│       ├── Metadata: 1.2s | 450 tokens | $0.003 | Halluc: 12%
│       └── Feedback: 👍 👎
└── Chat Input Bar: placeholder text + → Send gomb
```

**FONTOS:** Ezt a meglévő Figma design-t kell alapul venni + kiegészíteni:
- Model selector dropdown hozzáadása a Controls Bar-hoz
- Copy gomb az assistant válaszokhoz
- Prompt history kezelés (nem látható, de backend logika)
- Chat history persistence (localStorage)
- Scroll-to-bottom gomb
- "New Chat" / "Clear history" gomb aktiválása

### 7c. @untitledui/icons — Használandó ikonok

`@untitledui/icons` v0.0.22 (1180+ ikon) — import mintával: `import IconName from "@untitledui/icons/IconName"`

| Ikon | Felhasználás |
|------|-------------|
| `Copy01` / `Copy06` | Copy gomb assistant üzenetnél |
| `Check` | "Copied!" feedback |
| `ArrowDown` | Scroll-to-bottom gomb |
| `Send01` / `Send03` | Send gomb |
| `Trash01` | Clear history |
| `MessageSquare01` | Chat ikon / New Chat |
| `User01` | User avatar |
| `Stars02` / `Zap` | AI Assistant avatar |
| `ChevronDown` | Dropdown arrow |
| `ThumbsUp` / `ThumbsDown` | Feedback gombok |

---

## 8. Verifikáció

1. **Backend teszt:** `curl -X POST .../query -d '{"question":"test","model":"openai/gpt-4o-mini"}'` → `model_used` mező a válaszban
2. **TypeScript:** `cd aiflow-admin && npx tsc --noEmit` — 0 hiba
3. **Manuális teszt böngészőben:**
   - Üzenet küldés → bal-rendezett megjelenés avatar-ral (Figma design szerint)
   - Oldal újratöltés → history megmarad (localStorage)
   - Copy gomb hover → másolás → "Copied!" feedback
   - Fel/le nyíl → prompt history navigáció
   - Model váltás dropdown-nal → válasz tartalmazza a modell badge-et
   - Felfele görgetés → "scroll to bottom" gomb megjelenik
   - Clear history → üzenetek törlődnek
   - HU/EN toggle → minden szöveg változik
   - Preset kérdés kártyák kattinthatók (empty state)
   - Sources chip-ek megfelelően renderelődnek
   - Feedback gombok (👍👎) működnek
   - Role selector (Baseline/Mentor/Expert) pill-ek működnek
4. **Figma sync:** Frissíteni az AIFlow — RAG Chat frame-et a model selector-ral
