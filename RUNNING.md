# KPI Analytics — Run Instructions

## Prasyarat

| Tool | Versi minimal | Cek |
|------|--------------|-----|
| Docker Desktop | 24+ | `docker --version` |
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Ollama | latest | `ollama --version` |

---

## Struktur Direktori

```
projek_kp_2/
├── docker-compose.yml
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── app/          (main.py, database.py)
│   ├── models/       (6 ORM models)
│   ├── routers/      (dashboard, kpi, mcp, chatbot)
│   ├── services/     (etl, aggregation, ollama, context)
│   ├── schemas/      (pydantic schemas)
│   ├── scripts/      (seed.py)
│   └── etl_runner.py
└── frontend/
    └── src/
        ├── api/client.ts
        └── hooks/useKpiData.ts
```

---

## Langkah 1 — Jalankan PostgreSQL (Docker)

Dari folder root `projek_kp_2/`:

```bash
docker compose up -d
```

Tunggu hingga container healthy (~10 detik), cek dengan:

```bash
docker compose ps
```

Output yang diharapkan:
```
NAME           STATUS
kpi_postgres   Up (healthy)
```

---

## Langkah 2 — Setup Python Environment

```bash
cd projek_kp_2/backend

# Buat virtual environment
python -m venv venv

# Aktifkan (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Langkah 3 — Seed Database

> Jalankan dari folder `backend/` dengan venv aktif.

```bash
python scripts/seed.py
```

Output yang diharapkan:
```
✓ Seeded dim_division
✓ Seeded dim_kpi
✓ Seeded dim_period
✓ Seeded dim_period_mapping
✓ Seeded fact_kpi_performance (480 records)

✅ Database seeding complete!
   Run ETL next:  python etl_runner.py
```

---

## Langkah 3b — Migrasi Weight KPI (hanya jika database sudah ada sebelumnya)

> **Skip langkah ini jika fresh install** — `seed.py` sudah menyertakan weight.
> Jalankan ini hanya jika database sudah terisi sebelum weight ditambahkan.

```bash
python scripts/migrate_add_weight.py
```

Output yang diharapkan:
```
✓ Column 'weight' ensured on dim_kpi
✓ Weights updated for all KPIs

Current weight values:
  [ 1] Melaksanakan delivery inovasi       5.0%
  [ 2] Melakukan incident prevention       35.0%
  [ 3] SLA compliance                      60.0%
  ...

✅ Migration complete.
```

---

## Langkah 4 — Jalankan ETL

```bash
# Run ETL untuk semua tahun (2024 dan 2025)
python etl_runner.py --all

# Atau untuk tahun tertentu
python etl_runner.py --year 2025
python etl_runner.py --year 2024
```

Output yang diharapkan:
```
✅ ETL Success — year=2025
   Raw rows processed : 240
   Quarterly upserted : 60

✅ ETL Success — year=2024
   Raw rows processed : 240
   Quarterly upserted : 60
```

> Setelah ETL, tabel `fact_kpi_quarterly` akan berisi data agregasi.

---

## Langkah 5 — Jalankan FastAPI

```bash
# Dari folder backend/, venv aktif
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Output:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**API Docs** (Swagger UI): http://localhost:8000/docs  
**Health Check**: http://localhost:8000/

---

## Langkah 6 — Setup Ollama (untuk Chatbot)

Pastikan Ollama sudah terinstall, lalu pull model:

```bash
# Pull model
ollama pull qwen3:4b-instruct

# Jalankan Ollama server (jika belum running)
ollama serve
```

> Jika Ollama tidak running, API tetap berjalan normal — chatbot akan mengembalikan pesan error koneksi, dashboard tidak terpengaruh.

---

## Langkah 6b — Jalankan FastMCP Server (Chatbot Engine)

> **Terminal terpisah** dari FastAPI. Pastikan venv aktif.

```bash
cd projek_kp_2/backend
python mcp_server.py
```

Output:
```
INFO  __main__ -- Starting FastMCP Chat Server on port 8001
INFO  __main__ -- Ollama: http://localhost:11434 | Model: qwen3:4b-instruct
INFO  uvicorn -- Application startup complete.
INFO  uvicorn -- Uvicorn running on http://0.0.0.0:8001
```

Verifikasi:
```bash
# Health check
curl http://localhost:8001/

# Daftar tools
curl http://localhost:8001/tools

# Test chatbot
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "overview KPI 2025", "year": 2025}'
```

> FastMCP server (port 8001) menangani chatbot secara mandiri menggunakan Ollama native tool calling.
> Dashboard data tetap dilayani oleh FastAPI (port 8000).

---

## Langkah 7 — Jalankan Frontend

```bash
cd projek_kp_2/frontend

# Install dependencies (jika belum)
npm install

# Jalankan dev server
npm run dev
```

Frontend tersedia di: **http://localhost:8080**

---

## Verifikasi Endpoint

Gunakan browser, curl, atau Postman:

```bash
# Health check FastAPI
curl http://localhost:8000/

# Overview dashboard 2025
curl "http://localhost:8000/dashboard/overview?year=2025"

# Detail divisi Network (ID=1)
curl "http://localhost:8000/dashboard/division/1?year=2025"

# Trend divisi Network
curl "http://localhost:8000/dashboard/trend/1?year=2025"

# KPI underperform
curl "http://localhost:8000/dashboard/underperform?year=2025"

# Health check FastMCP server
curl http://localhost:8001/

# Daftar MCP tools
curl http://localhost:8001/tools

# Test chatbot (FastMCP)
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Divisi mana yang paling underperform di 2025?", "year": 2025}'
````

---

## Re-run ETL Setelah Input Data Baru

Setelah memasukkan data via `POST /kpi/realization`, jalankan ulang ETL:

```bash
python etl_runner.py --year 2026
```

---

## Division ID Reference

| ID | Division Name    | Slug (URL)         | Eval Period |
|----|------------------|--------------------|-------------|
| 1  | Network          | `/network`         | H (Half Year) |
| 2  | Software Engineer| `/software-engineer`| Q (Quarter) |
| 3  | Sales Executive  | `/sales-executive` | Q (Quarter) |
| 4  | HR Officer       | `/hr-officer`      | M (Monthly) |

---

## MCP Tools Reference

| Tool | Required Params | Deskripsi |
|------|----------------|-----------|
| `get_overview_kpi` | `year` | Overview semua divisi |
| `get_division_kpi` | `division_id`, `year` | Detail KPI satu divisi |
| `get_kpi_trend` | `division_id`, `year` | Tren YoY per divisi |
| `get_underperforming_kpi` | `year` | KPI dengan achievement < 80% |
| `compare_divisions` | `year` | Ranking antar divisi |

---

## Troubleshooting

### PostgreSQL gagal connect
- Pastikan Docker Desktop running
- Cek port 5432 tidak dipakai: `netstat -an | findstr 5432`
- Lihat log: `docker compose logs postgres`

### Seed gagal duplicate key
- Data sudah ada — ini normal jika seed dijalankan dua kali
- Script aman: mengecek `if count == 0` sebelum insert

### ETL: "No raw data found"
- Pastikan seed sudah dijalankan lebih dulu
- Cek: `docker compose exec postgres psql -U kpi_user -d kpi_warehouse -c "SELECT COUNT(*) FROM fact_kpi_performance;"`

### Chatbot: "Cannot connect to Ollama"
- Jalankan `ollama serve` di terminal terpisah
- Cek: `curl http://localhost:11434/api/tags`
- Pastikan `mcp_server.py` juga sudah running (port 8001)

### Chatbot: "Tool error"
- Periksa log di terminal `mcp_server.py`
- Pastikan PostgreSQL accessible dari backend (`DATABASE_URL` di `.env` benar)

### FastMCP server gagal start
- Pastikan `fastmcp` sudah terinstall: `pip install fastmcp`
- Cek port 8001 tidak dipakai: `netstat -an | findstr 8001`

### Frontend: data tidak muncul
- Pastikan FastAPI running di port 8000
- Pastikan FastMCP server running di port 8001 (untuk chatbot)
- Cek CORS — sudah diset `allow_origins=["*"]`
- Buka DevTools -> Network, lihat response dari `/dashboard/overview`
