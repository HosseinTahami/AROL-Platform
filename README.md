# AROL Customer Platform

Multi-Agent AI Framework for Industrial Fleet Management and Autonomous
Troubleshooting. (**AROL S.p.A**)

A customer platform for AROL's machine fleet: a conversational assistant that
reasons over machine manuals (PDF), operational data (alarms, telemetry,
maintenance), and commercial data (quotes, orders) to support plant operators.

An orchestrator interprets each request, and decides which agents are needed. It is strict about the data it shares, per-company and per-role access control.


## 1. ARCHITECTURE OVERVIEW

- **Backend**  : Python + Django + Django REST Framework

- **Database** : PostgreSQL with the pgvector extension (structured data + embeddings)

- **Frontend** : React (Vite), plain JavaScript

- **AI/LLM**   : Local models via Ollama, orchestrated with LangGraph

             - qwen3.5:9b        (reasoning / agents / planning / synthesis)

             - nomic-embed-text  (768-dim embeddings for retrieval)

Request flow:
  User (React chat)
    -> POST /api/chat/  (token-authenticated)
      -> Orchestrator (LangGraph state graph)
           **1. scope_check :** The target machine must belong to the user's own company, or the request is refused immediately.
           **2. planner:** LLM selects one OR MORE specialist domains needed to answer the user's question
                - Manuals : procedures, specifications, general how-to from the machine manual 
                - Diagnosis : cause and remedy of a SPECIFIC alarm the machine has raised (combines the alarm log with a RAG search of that machine's manual) 
                - Operational : alarm history, telemetry, machine health, maintenance tickets 
                - Commercial : orders, quotes, revision history, prices, deliveries
            **3. visibility_check:** Every selected domain is checked against the user's role (full / technician / commercial); any disallowed domain causes an explicit refusal.
            **4. run_agents :** Every selected specialist runs and returns its own grounded answer (+ sources, where relevant). 
           **5. synthesizer :** if only one specialist ran, its answer is returned as-is; if more than one ran, an LLM call merges them into a single coherent answer. -> JSON response: the answer, which agent(s) handled it, manual page citations (where applicable), whether it was refused, and a full execution trace (which nodes ran, in order).

The orchestrator is a LangGraph state graph so it can plan and combine more than one specialist per question (e.g. "is this alarm covered by warranty?" invokes both diagnosis and commercial and merges their findings). for more information and explanation you can check the documentation. ***(for the full design rationale, including why LangGraph was adopted and why the four specialist domains were chosen.)***

## 2. REQUIREMENTS

- **Python 3.**

- **PostgreSQL** with the **pgvector** extension installed

- **Node.js** and **npm** (for the frontend)

- **Ollama** with a CUDA-capable GPU recommended

    Tested on an NVIDIA RTX 4060 (8 GB VRAM) --> **Zephyrus G16 GU605MV** 

- **uv** for Python env / packages --> Conda or even plain pip can be used to but uv is recommended, since it is fast and easy to use.


## 3. SETUP

**3.1** Clone and enter the project
---
```bash
    git clone <repository-url>
    cd AROL-Platform
```


**3.2** Local LLM models (Ollama)
---
```bash
    ollama pull qwen3.5:9b
    ollama pull nomic-embed-text
```
Ollama must be running (it serves a local API on port 11434 by default).


**3.3** PostgreSQL database
---
Create a database and a user, and enable the pgvector extension:

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

If you change these values, update backend/config/settings.py (DATABASES).


**3.4** Backend (Djanog)
---
```bash
    cd backend
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
```
```bash
    python manage.py migrate
    python manage.py createsuperuser      
```

**NOTE:** the `python manage.py createsuperuser` is for creating an admin acount so you can have access to admin pannel in djano.


**3.5** Frontend (React)
---
```
    cd ../frontend
    npm install
```

## 4. LOADING THE DATA


**4.1** Structured data (Excel workbook -> PostgreSQL)
---

```bash
    python manage.py import_data --file <path-to-dataset.xlsx>
```

**NOTE**: `import_data` is a custome django-admin command for importing data from the **specific** Excel workbook to PostgreSQL.

Example:

```bash
    python manage.py import_data --file ../data/AROL_Q2_synthetic_fleet_dataset.xlsx
```

Parameters:

```
    --file   (required)  Path to the .xlsx workbook (one sheet per entity).
```

This imports the 12 entities in dependency order. Re-running the command is not going to create duplicates rows in the database but only update them in case of any change. All the users are given the password 'arol1234' for testing.

**4.2** Manuals (PDF -> chunks -> embeddings)
---

```bash
    python manage.py ingest_manuals --dir <path-to-manuals-folder>
```

**NOTE:** `ingest_manuals` is a custome django-admin command for converting the pdf files into chunks of data and then save them as vectors.

Example:

```
    python manage.py ingest_manuals --dir ../data/manuals
```

Parameters:
    --dir    (required)  Folder containing the manual PDFs.

Each PDF is named "<serialNumber>_manual_EN.pdf". The command extracts text,
splits it into overlapping ~600-character chunks, embeds each chunk with
nomic-embed-text, and stores them linked to the machine with that serial
number. It is re-runnable (old chunks for a file are replaced).


## 5. RUNNING THE APPLICATION

Start three processes (Ollama, backend, frontend).

Ollama:      (usually already running as a service)


```bash
    ollama list  
```

```bash        
    NAME                       ID              SIZE      MODIFIED   
    qwen3.5:9b                 6488c96fa5fa    6.6 GB    7 days ago    
    nomic-embed-text:latest    0a109f422b47    274 MB    7 days ago   
```
**Note:** Use `ollama list` to make sure you have already pulled and downloaded the right models.

```
    ollama serve
```

Backend:     from backend/, with the venv active

```
    python manage.py runserver 8001
```


Frontend:    from frontend/

```
    npm run dev
```

Then open the URL printed by Vite (default http://localhost:5173).

Log in with an imported user, e.g.:
```
    username: elena.fabbri@valgrande.example   (visibility: full)
    password: arol1234
```

QR-code entry: the machine can be preselected via the URL, e.g.
```
    http://localhost:5173/?machine=MCH-0001
```

## 6. EVALUATION

A single command reproduces all metrics against a frozen benchmark stored in
evaluation/ (eval_questions.json, rag_questions.json). The benchmark is fixed
so that different models can be compared on identical questions.

    python manage.py evaluate

Parameters (all optional):
    --routing  Path to routing benchmark   (default evaluation/eval_questions.json)
    --rag      Path to RAG benchmark        (default evaluation/rag_questions.json)
    --k        Top-k for retrieval recall   (default 5)

It reports:
    - Routing accuracy         (the planner selects the right domain(s) for
                                each question)
    - Security enforcement     (visibility rules refuse the wrong role)
    - Company isolation        (a user cannot access another company's machines)
    - Multi-agent coordination (genuinely cross-domain questions correctly
                                trigger all of their required specialist agents)
    - RAG retrieval quality    (Recall@k and MRR)


## 7. DATASET FORMATS

7.1 Structured data: one .xlsx workbook, one sheet per entity
---

| Sheet Name | Key Columns (camelCase) |
| --- | --- |
| **Companies** | companyId, companyName, country, sector, city, currency, locale |
| **Users** | userId, companyId, firstName, lastName, email, jobTitle, visibility (full | technician | commercial) |
| **MachineModels** | modelId, modelCode, description, primitiveDiameter, nominalHeads, containerType, capType, industrySegment, notes |
| **Machines** | machineId, companyId, modelId, serialNumber, deliveryDate, plantLocation, configurationProfile, plcFamily, softwareVersion |
| **Quotes** | quoteId, companyId, currency, createdAt, validUntil, description |
| **QuoteRevisions** | quoteRevisionId, quoteId, revisionNumber, revisionStatus, issuedAt, discountRate, changeSummary |
| **QuoteLines** | quoteLineId, quoteRevisionId, machineId, price, description |
| **Orders** | orderId, quoteId, companyId, orderStatus, orderDate, expectedDeliveryDate, shipmentStatus, currency, notes |
| **OrderLines** | orderLineId, orderId, fulfillmentStatus |
| **TelemetrySnapshots** | telemetryId, machineId, timestamp, operationalStatus, productionRateBph, uptimePercentage, alarmCount, temperatureC, energyKwh, healthNote |
| **Alarms** | alarmId, machineId, timestamp, alarmCode, severity, alarmStatus |
| **MaintenanceTickets** | ticketId, machineId, alarmId, ticketType, ticketStatus, priority, createdDate, ownerRole |


Notes:
    - IDs are preserved as primary keys, so the join keys in the workbook map
      directly onto database relationships.
    - Some columns are intentionally empty (e.g. QuoteLines.machineId,
      MaintenanceTickets.alarmId, MachineModels.primitiveDiameter); these are
      handled as optional / nullable during import.
    - Order contents are derived from the approved quote revision's lines;
      OrderLines carry only a fulfillment status.

7.2 Manuals: PDF files
---
    - One PDF per machine, named "<serialNumber>_manual_EN.pdf".
    - The serial number in the filename links the manual to its machine.
    - English only.


## 8. ACCESS CONTROL SUMMARY

Every request is scoped twice, both checks enforced in the orchestrator before any specialist runs:

    Company isolation : a user only ever sees data for machines owned by
                        their own company; out-of-scope requests are refused
                        explicitly (never answered, never returned empty).

    Visibility         : full        -> manuals + diagnosis + operational + commercial
                        technician    -> manuals + diagnosis + operational
                        commercial    -> manuals + commercial

Note that "diagnosis" (explaining a specific alarm's cause and remedy) is gated the same way as "operational" data, since it draws on the same alarm/telemetry information plus the manual.


## 9. PROJECT LAYOUT

    AROL-Platform/
      backend/
        config/            Django project (settings, urls)
        core/              data models, REST API, data-loading commands
          management/commands/  import_data, ingest_manuals
        ai/                agents, orchestrator, evaluate command
      frontend/            React + Vite chat interface
      evaluation/          frozen benchmark question sets
      README.md