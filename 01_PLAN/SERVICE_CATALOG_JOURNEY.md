# Service Catalog — User Journey (S4)

> **Fazis:** S4 (v1.2.1 Production Ready Sprint)
> **Felhasznalo:** Admin — osszes szolgaltatas attekintese, pipeline inditasa

---

## 1. Journey

```
Dashboard → Services (sidebar) → Service kartyak → Pipeline inditasa / Detail megtekintese
```

## 2. Lepesek

### 2.1 Service Catalog oldal (/services)
- 16+ service kartya grid elrendezesben
- Kartya: nev, leiras, statusz badge (available/unavailable), has_adapter jelzo
- Szures: search by name, filter adapter=true/false
- "Run Pipeline" gomb adapter-es service-eknel → navigal /pipelines-ra

### 2.2 Pipeline integracio meglevo oldalakon
- Documents: "Automate with Pipeline" gomb
- Emails: "Setup Email Triage" gomb
- RAG: "Advanced Ingest" gomb
- ProcessDocs: "Batch Process" gomb

## 3. API

| Method | Endpoint | Allapot |
|--------|----------|---------|
| GET | `/api/v1/services/manager` | KESZ (v1.2.0) |

## 4. Sikerkriteriuok

- [ ] /services betolt, kartyak source=backend
- [ ] Search szures mukodik
- [ ] Pipeline gombok navigalnak
- [ ] 0 console error, i18n HU/EN
