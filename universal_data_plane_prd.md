# Universal Data Plane — Product Requirements Document

**Project Codename:** Semantic Mesh  
**Version:** 0.1 (MVP — In-Memory Graph, No AI)  
**Author:** Draft  
**Status:** Planning

---

## 1. Vision & Problem Statement

Modern organizations accumulate data across dozens of siloed systems — transactional databases, event streams, SaaS platforms, internal apps. These systems have no shared language. The same concept (e.g., "customer", "account", "transaction") means different things in different systems, has inconsistent data types, and is governed by no single source of truth.

**The Universal Data Plane** solves this by introducing a semantic layer that sits above all systems and provides:

- A **Business Glossary** — canonical definitions of every business term, metric, and concept.
- An **Ontology** — formal, machine-readable structure of entities, attributes, and relationships across the organization.
- A **Knowledge Graph** — a live instantiation of the ontology populated with actual data relationships.
- A **Data Intelligence Layer** — federated, vector-indexed access so agents, ML models, apps, and BI tools can query the semantic layer with natural language or structured queries.

---

## 2. System Architecture (Full Vision)

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  [ Databases ]  [ Event Streams ]  [ Apps ]  [ API Channels ]   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ raw data + schema
┌──────────────────────────▼──────────────────────────────────────┐
│                     GOVERNANCE LAYER                            │
│  [ System of Records (SOR) ]   [ System of Objects (SOO) ]      │
│  Data lineage, ownership, PII flags, data contracts             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ governed, labelled entities
┌──────────────────────────▼──────────────────────────────────────┐
│                    SEMANTIC LAYER                               │
│         ┌──────────────────────────────────────────┐           │
│         │          Business Glossary                │           │
│         │  Canonical definitions of all terms,      │           │
│         │  metrics, and concepts across the org.    │           │
│         └──────────────────────────────────────────┘           │
│         ┌──────────────────────────────────────────┐           │
│         │       Ontology (Entity Model)             │           │
│         │  Entity classes, typed attributes,        │           │
│         │  cardinality, relationships, constraints  │           │
│         └──────────────────────────────────────────┘           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ structured semantic model
┌──────────────────────────▼──────────────────────────────────────┐
│              KNOWLEDGE GRAPH (Neo4j / In-Memory)                │
│   Ontology + Data = Nodes (entities) + Edges (relationships)    │
│   Entity resolution, cross-system identity linking              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ queryable graph
┌──────────────────────────▼──────────────────────────────────────┐
│                   DATA INTELLIGENCE LAYER                       │
│  [ Federated Query ]  [ Semantic Cache ]  [ Vector Index ]      │
│  Unified access API for downstream consumers                    │
└─────────┬────────────────┬──────────────────┬───────────────────┘
          │                │                  │
    ┌─────▼──────┐  ┌──────▼──────┐  ┌───────▼──────────┐
    │   Agents   │  │  ML Models  │  │  Apps / BI Tools  │
    └────────────┘  └─────────────┘  └──────────────────┘
```

---

## 3. Component Deep-Dive

### 3.1 Business Glossary

A centralized repository structured as a document store or relational table with the following attributes per term:

| Field | Type | Description |
|---|---|---|
| `term_id` | UUID | Unique identifier |
| `name` | string | Canonical name (e.g., "Net Revenue") |
| `domain` | enum | Business domain (Finance, Risk, Customer, etc.) |
| `definition` | text | Plain-English description |
| `synonyms` | string[] | Aliases used in source systems |
| `owner` | string | Business owner / steward |
| `linked_entities` | UUID[] | Ontology entity IDs this term maps to |
| `source_systems` | string[] | Where this concept appears |
| `tags` | string[] | Searchable tags |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### 3.2 Ontology (Entity Model)

The ontology defines the formal structure of the domain. It is the schema of the knowledge graph.

**Entity Classes** — examples for a financial organization:
- `Customer`, `Account`, `Transaction`, `Product`, `Employee`, `Branch`, `Counterparty`, `Instrument`, `Portfolio`

**Attributes** — typed fields per entity class:
- `Customer.customer_id` (UUID, PK), `Customer.kyc_status` (enum), `Customer.risk_tier` (int)

**Relationships** — directed, typed edges:
- `(Customer)-[:HOLDS]->(Account)`
- `(Account)-[:LINKED_TO]->(Transaction)`
- `(Employee)-[:MANAGES]->(Portfolio)`
- `(Transaction)-[:REFERENCES]->(Instrument)`

**Cardinality annotations:**
- one-to-one, one-to-many, many-to-many per relationship type

### 3.3 Knowledge Graph

Neo4j (production) / NetworkX in-memory (MVP) stores the ontology as a live graph:

- **Nodes** = entity instances with properties from source systems
- **Edges** = typed relationships inferred from foreign keys, joins, and event correlation
- **Labels** = entity class (`:Customer`, `:Account`)
- **Properties** = flattened attributes from the business glossary mapping

**Graph population pipeline:**

```
Source Schema (SQL DDL / JSON schema)
       │
  [ Schema Parser ] ─── extracts tables, columns, FKs
       │
  [ Entity Mapper ] ─── maps tables → ontology entity classes
       │
  [ Edge Resolver ] ─── FK constraints → relationship edges
       │
  [ Graph Builder ] ─── NetworkX DiGraph (MVP) / Neo4j (prod)
       │
  [ Visualizer ]   ─── pyvis HTML / D3.js interactive view
```

### 3.4 Data Intelligence Layer (Future)

| Component | Technology | Role |
|---|---|---|
| Federated Query | Apache Arrow Flight / GraphQL | Unified query across sources |
| Semantic Cache | Redis + embedding fingerprint | Avoid redundant traversals |
| Vector Index | Chroma / Qdrant | Semantic search over glossary + graph |
| LLM Integration | Claude / OpenAI | NL → Cypher/GraphQL translation |

---

## 4. MVP Scope (Phase 1)

### Goal

Given a **code repository** and/or a **database schema file** as input, automatically extract the entity model and render an interactive in-memory knowledge graph — no Neo4j, no AI, no live data.

### What it does

1. Accepts input: Python/JS/Java code files OR SQL DDL / JSON schema
2. Parses entities (tables/classes/models), attributes (columns/fields), and relationships (FK, imports, associations)
3. Constructs an in-memory directed graph using NetworkX (Python)
4. Generates an interactive HTML visualization using pyvis
5. Outputs a browsable graph showing nodes (entities), edges (relationships), and field-level metadata

### What it does NOT do (Phase 1)

- No live database connections
- No AI/LLM enrichment
- No Neo4j
- No business glossary UI
- No vector search
- No federated queries

---

## 5. Input Specification

### Input A: SQL DDL / Schema File

Supported formats:
- `.sql` files with `CREATE TABLE` statements
- PostgreSQL schema dumps
- Supabase schema JSON
- Prisma schema (`.prisma`)
- JSON Schema documents

**Sample input:**

```sql
CREATE TABLE customers (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  kyc_status VARCHAR(50),
  created_at TIMESTAMPTZ
);

CREATE TABLE accounts (
  id UUID PRIMARY KEY,
  customer_id UUID REFERENCES customers(id),
  account_type VARCHAR(50),
  balance DECIMAL(18,2)
);

CREATE TABLE transactions (
  id UUID PRIMARY KEY,
  account_id UUID REFERENCES accounts(id),
  amount DECIMAL(18,2),
  txn_type VARCHAR(50),
  created_at TIMESTAMPTZ
);
```

### Input B: Code Files

Supported:
- Python (SQLAlchemy models, Pydantic schemas, dataclasses)
- JavaScript/TypeScript (Mongoose schemas, Sequelize models, TypeORM entities)
- Java (JPA/Hibernate annotations)

**Sample Python input:**

```python
class Customer(Base):
    __tablename__ = "customers"
    id = Column(UUID, primary_key=True)
    name = Column(String)
    accounts = relationship("Account", back_populates="customer")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(UUID, primary_key=True)
    customer_id = Column(UUID, ForeignKey("customers.id"))
    customer = relationship("Customer", back_populates="accounts")
```

---

## 6. Graph Construction Logic

### Entity Extraction Rules

| Source | Maps to | Entity Type |
|---|---|---|
| SQL `CREATE TABLE` | Node (entity class) | Table name → PascalCase label |
| SQL column | Node property | Column name → attribute |
| SQL `REFERENCES` / FK | Directed edge | `(A)-[:FK_TO]->(B)` |
| Python class inheriting `Base` | Node | Class name → label |
| SQLAlchemy `relationship()` | Directed edge | Relationship name → edge type |
| ForeignKey() annotation | Directed edge | Matches FK to target table |

### Graph Schema (NetworkX)

```python
import networkx as nx

G = nx.DiGraph()

# Add entity node
G.add_node("Customer", type="entity", attributes=["id", "name", "kyc_status"])

# Add relationship edge
G.add_edge("Account", "Customer",
           relationship="BELONGS_TO",
           cardinality="many-to-one",
           via="customer_id")
```

### Node metadata stored per entity:
- `type`: "entity" or "attribute" (optional exploded view)
- `source_table`: original table/class name
- `attributes`: list of field names
- `attribute_types`: dict of field → data type
- `pks`: list of primary key fields
- `fks`: list of foreign key fields

### Edge metadata stored per relationship:
- `relationship`: inferred label (e.g., `HOLDS`, `LINKED_TO`)
- `cardinality`: `"1:N"`, `"N:1"`, `"M:N"`
- `via`: FK column name
- `source_system`: which input file

---

## 7. Visualization Layer (Phase 1)

### Tooling
- **pyvis** for interactive HTML output (wraps vis.js)
- Color coding:
  - Core entities (tables with FKs pointing to them) → `#7F77DD` (purple)
  - Leaf entities (no inbound FKs) → `#1D9E75` (teal)
  - Junction/bridge tables → `#BA7517` (amber)
- Node size scales with attribute count
- Edge labels show relationship type + FK column
- Click to expand: shows all attributes of selected entity
- Export: single-file `graph.html` — open in any browser, no server needed

### Visualization features (Phase 1)
- [ ] Pan/zoom navigation
- [ ] Node hover tooltip: entity name, attribute count, PK/FK summary
- [ ] Edge hover tooltip: relationship type, via column, cardinality
- [ ] Click node → sidebar shows all attributes with types
- [ ] Filter by: entity type, source file
- [ ] Toggle: show/hide attribute nodes (compact vs expanded view)
- [ ] Export graph JSON (for future Neo4j import)

---

## 8. Phase Roadmap

### Phase 1 — In-Memory Graph (Current)
- SQL + code parser
- NetworkX graph construction
- pyvis HTML visualization
- Zero external dependencies

### Phase 2 — Graph Database + Glossary
- Migrate to Neo4j or ArangoDB
- Build business glossary UI (React + FastAPI)
- Cypher query interface
- Schema drift detection (compare v1 vs v2 graphs)

### Phase 3 — AI Integration
- LLM-powered term auto-classification
- NL → Cypher query translation
- Glossary auto-population from entity metadata
- Embedding-based similarity search across entities

### Phase 4 — Data Intelligence Layer
- Vector index over glossary + graph nodes
- Federated query API (GraphQL or REST)
- Agent-accessible endpoint
- BI tool connector (dbt integration, Looker/Metabase)

---

## 9. Tech Stack

| Layer | Phase 1 | Phase 2+ |
|---|---|---|
| Language | Python 3.11+ | Python + TypeScript |
| Graph (in-memory) | NetworkX | — |
| Graph (persistent) | — | Neo4j 5.x |
| SQL parsing | `sqlglot` | same |
| Code parsing | `ast` (Python), `tree-sitter` | same |
| Visualization | pyvis | D3.js / React Force Graph |
| API | None | FastAPI |
| Frontend | Static HTML | Next.js |
| Vector DB | None | Chroma / Qdrant |

---

## 10. File Structure (Phase 1)

```
semantic-mesh/
├── ingestion/
│   ├── sql_parser.py        # Parses DDL → entity + FK model
│   ├── code_parser.py       # Parses Python/TS models → entity model
│   └── schema_normalizer.py # Unifies output format from both parsers
├── graph/
│   ├── builder.py           # NetworkX graph construction
│   ├── enricher.py          # Infers relationship labels, cardinalities
│   └── exporter.py          # Exports to JSON / Cypher / pyvis HTML
├── viz/
│   ├── renderer.py          # pyvis config + HTML generation
│   └── templates/           # HTML templates for the output page
├── cli.py                   # Entry point: python cli.py --input schema.sql
├── requirements.txt
└── README.md
```

---

## 11. CLI Usage (Phase 1)

```bash
# From a SQL file
python cli.py --input schema.sql --output graph.html

# From a Python models file
python cli.py --input models.py --type python --output graph.html

# From a directory of code files
python cli.py --input ./src --type auto --output graph.html --format html

# Export as JSON for future Neo4j import
python cli.py --input schema.sql --output graph.json --format json
```

---

## 12. Success Metrics (Phase 1)

| Metric | Target |
|---|---|
| Parse accuracy on standard SQL DDL | ≥ 95% of tables + FKs captured correctly |
| Graph render time (< 100 nodes) | < 3 seconds |
| Output portability | Single `.html` file, no server needed |
| Entity coverage | All tables with ≥1 column extracted |
| Relationship coverage | All FK constraints mapped as edges |

---

## Appendix A: Sample Output — Business Glossary Entry

```json
{
  "term_id": "bgt-0042",
  "name": "Net Revenue",
  "domain": "Finance",
  "definition": "Total revenue recognized after deducting returns, discounts, and allowances. Calculated as Gross Revenue minus Returns and Allowances.",
  "synonyms": ["net_revenue", "revenue_net", "NR"],
  "formula": "gross_revenue - returns - allowances",
  "linked_entities": ["e-transactions", "e-accounts"],
  "source_systems": ["core_banking", "reporting_db"],
  "owner": "Head of Finance Analytics",
  "tags": ["KPI", "P&L", "revenue"],
  "created_at": "2025-01-15T09:00:00Z"
}
```

## Appendix B: Sample Neo4j Cypher (Future Phase)

```cypher
// Create entities
CREATE (c:Customer {id: 'cust_001', name: 'Acme Corp', kyc_status: 'verified'})
CREATE (a:Account {id: 'acc_001', account_type: 'current', balance: 50000.00})
CREATE (t:Transaction {id: 'txn_001', amount: 1500.00, txn_type: 'credit'})

// Create relationships
MATCH (c:Customer {id: 'cust_001'}), (a:Account {id: 'acc_001'})
CREATE (c)-[:HOLDS {since: '2024-01-01'}]->(a)

MATCH (a:Account {id: 'acc_001'}), (t:Transaction {id: 'txn_001'})
CREATE (a)-[:LINKED_TO {via: 'account_id'}]->(t)

// Query: all transactions for a customer
MATCH (c:Customer {id: 'cust_001'})-[:HOLDS]->(a:Account)-[:LINKED_TO]->(t:Transaction)
RETURN c.name, a.account_type, t.amount, t.txn_type
ORDER BY t.amount DESC
```
