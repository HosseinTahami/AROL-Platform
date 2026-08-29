# AROL Customer Platform

Multi-Agent AI Framework for Industrial Fleet Management and Autonomous
Troubleshooting, built for AROL S.p.A.

A conversational assistant that reasons over machine manuals (PDF),
operational data (alarms, telemetry, maintenance), and commercial data
(quotes, orders). An orchestrator decides which specialist agent(s) answer
each question, with per-company and per-role access control.


## 1. STACK

- Backend: Python + Django + Django REST Framework
- Database: PostgreSQL + pgvector
- Frontend: React (Vite)
- AI: local models via Ollama, orchestrated with LangGraph
    - qwen3.5:9b (reasoning / agents / planning)
    - nomic-embed-text (768-dim embeddings)


## 2. REQUIREMENTS

- Python 3
- PostgreSQL with the pgvector extension
- Node.js + npm
- Ollama (GPU recommended; tested on an RTX 4060, 8 GB VRAM)
- uv (or plain pip/conda)


## 3. SETUP

3.1 Clone
```bash
git clone <repository-url>
cd AROL-Platform
```

3.2 Pull the local models
```bash
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```
Ollama must be running (default: http://localhost:11434).

3.3 Create the database
```bash
sudo -u postgres psql
CREATE DATABASE arol;
CREATE USER arol_user WITH PASSWORD 'arol_pass';
GRANT ALL PRIVILEGES ON DATABASE arol TO arol_user;
ALTER DATABASE arol OWNER TO arol_user;
\c arol
CREATE EXTENSION IF NOT EXISTS vector;
\q
```
If you use different values, update `backend/config/settings.py` (DATABASES).

3.4 Backend
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

3.5 Frontend
```bash
cd ../frontend
npm install
```


## 4. LOADING THE DATA

4.1 Structured data (Excel -> PostgreSQL)
```bash
python manage.py import_data --file <path-to-dataset.xlsx>
```
Parameters:
- `--file` (required) - path to the .xlsx workbook (one sheet per entity)

Imports all entities in dependency order. Re-running updates existing rows
instead of duplicating them. Imported users get the password `arol1234`.

4.2 Manuals (PDF -> chunks -> embeddings)
```bash
python manage.py ingest_manuals --dir <path-to-manuals-folder>
```
Parameters:
- `--dir` (required) - folder containing the manual PDFs

Each PDF must be named `<serialNumber>_manual_EN.pdf`. Text is extracted,
split into overlapping ~600-character chunks, embedded, and stored linked
to the matching machine. Re-runnable (old chunks are replaced).


## 5. RUNNING

Start three processes:

```bash
ollama serve                      # if not already running

cd backend && python manage.py runserver 8001

cd frontend && npm run dev
```

Open the URL printed by Vite (default http://localhost:5173).

Log in with an imported user, e.g.:
```
username: elena.fabbri@valgrande.example
password: arol1234
```

The machine can be preselected via URL (QR-code entry point):
```
http://localhost:5173/?machine=MCH-0001
```


## 6. EVALUATION

```bash
python manage.py evaluate
```
Parameters (all optional):
- `--routing` - routing benchmark (default `evaluation/eval_questions.json`)
- `--multi-agent` - multi-agent benchmark (default `evaluation/multi_agent_questions.json`)
- `--rag` - RAG benchmark (default `evaluation/rag_questions.json`)
- `--answers` - answer-quality benchmark (default `evaluation/answer_questions.json`)
- `--k` - top-k for retrieval recall (default `5`)

Reports routing accuracy, multi-agent coordination, RAG retrieval quality
(Recall@k, MRR), and answer quality (LLM-as-judge, scored 1-5). See
DOCUMENTATION.md for full methodology and results.


## 7. DATASET FORMATS

7.1 Structured data - one .xlsx workbook, one sheet per entity:

| Sheet | Key columns |
|---|---|
| Companies | companyId, companyName, country, sector, city, currency, locale |
| Users | userId, companyId, firstName, lastName, email, jobTitle, visibility (full/technician/commercial) |
| MachineModels | modelId, modelCode, description, primitiveDiameter, nominalHeads, containerType, capType, industrySegment, notes |
| Machines | machineId, companyId, modelId, serialNumber, deliveryDate, plantLocation, configurationProfile, plcFamily, softwareVersion |
| Quotes | quoteId, companyId, currency, createdAt, validUntil, description |
| QuoteRevisions | quoteRevisionId, quoteId, revisionNumber, revisionStatus, issuedAt, discountRate, changeSummary |
| QuoteLines | quoteLineId, quoteRevisionId, machineId, price, description |
| Orders | orderId, quoteId, companyId, orderStatus, orderDate, expectedDeliveryDate, shipmentStatus, currency, notes |
| OrderLines | orderLineId, orderId, fulfillmentStatus |
| TelemetrySnapshots | telemetryId, machineId, timestamp, operationalStatus, productionRateBph, uptimePercentage, alarmCount, temperatureC, energyKwh, healthNote |
| Alarms | alarmId, machineId, timestamp, alarmCode, severity, alarmStatus |
| MaintenanceTickets | ticketId, machineId, alarmId, ticketType, ticketStatus, priority, createdDate, ownerRole |

Notes:
- Source IDs are used as primary keys; workbook join columns map directly
  onto database relationships.
- Some columns are intentionally empty (e.g. QuoteLines.machineId,
  MaintenanceTickets.alarmId) and are handled as optional during import.
- Order contents are derived from the approved quote revision's lines;
  OrderLines carry only a fulfillment status.

7.2 Manuals - PDF files:
- One PDF per machine, named `<serialNumber>_manual_EN.pdf`.
- English only.


## 8. PROJECT LAYOUT

```
AROL-Platform/
  backend/
    config/            Django project (settings, urls)
    core/              data models, REST API, data-loading commands
    ai/
      agents/            manuals_agent, commercial_agent, operational_agent
      orchestrator/       graph.py - the LangGraph orchestrator
      management/commands/  evaluate
  frontend/            React + Vite chat interface
  evaluation/          frozen benchmark question sets
  README.md
  DOCUMENTATION.md
```
