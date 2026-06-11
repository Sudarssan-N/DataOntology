# Banking Domain Ontology for the Semantic Data Layer

**Version 0.1 — Design Specification**

---

## 1. Design Principles

The ontology is organized into **three planes**, connected by typed, confidence-scored relationships:

| Plane | Question it answers | Example entities |
|---|---|---|
| **Business Plane** | What does the bank *do*? | Customer, Account, Account Opening process |
| **Semantic Plane** | What does data *mean*? | "Customer ID" concept, PII classification, Customer data domain |
| **Technical Plane** | Where does data *live and move*? | `cust_master` table, KYC API, AML pipeline |

**Core principles:**

1. **Don't invent — align.** Business concepts map to **FIBO** (Financial Industry Business Ontology), process/capability decomposition follows **BIAN** service domains, and message semantics align with **ISO 20022**. This makes the ontology defensible to architects and regulators, and lets you import existing definitions instead of writing thousands by hand.
2. **The Semantic Plane is the bridge.** Technical artifacts (columns, API fields) never link directly to business entities. They link to a **DataConcept** in the semantic plane, which links to the business entity. This is what lets `cust_id`, `customer_no`, and `party_key` across 40 systems resolve to one thing.
3. **Every edge carries provenance and confidence.** Tier 1 (deterministic), Tier 2 (heuristic), Tier 3 (AI-inferred). Queries can filter by minimum confidence.
4. **Processes are first-class citizens.** "Account Opening" is a node, not a tag. This is what enables the flagship query: *"show me everything account opening touches."*
5. **Extensible core.** The core ontology is fixed and versioned; teams extend via subtyping (e.g., `WealthAccount` is_a `Account`), never by mutating core classes.

---

## 2. Business Plane

### 2.1 Party & Roles

| Entity | Definition | Key attributes |
|---|---|---|
| `Party` | Any legal entity the bank interacts with | party_id, party_type, legal_name, jurisdiction |
| `Person` (is_a Party) | Natural person | date_of_birth, nationality, tax_residency |
| `Organization` (is_a Party) | Legal entity | registration_no, industry_code (NAICS/NIC), incorporation_date |
| `PartyRole` | A role a Party plays *in a context* | role_type, valid_from, valid_to |

**Role subtypes:** `Customer`, `Prospect`, `Guarantor`, `Beneficiary`, `AuthorizedSignatory`, `Nominee`, `Employee`, `Vendor`, `Correspondent`.

> **Why Party/Role separation matters:** the same person can be a customer, a guarantor on someone else's loan, and an employee. Banks that model "Customer" as the root entity end up with duplicate identities — the #1 cause of broken lineage and failed 360° views.

### 2.2 Products & Agreements

| Entity | Definition | Key attributes |
|---|---|---|
| `Product` | A marketable banking offering | product_code, product_family, status, launch_date |
| `ProductFeature` | A configurable capability of a product | feature_type, parameters |
| `Agreement` | Contract binding Party to Product terms | agreement_id, status, signed_date, terms_version |
| `Account` | Instantiation of an Agreement that holds value/positions | account_no, currency, status, opened_date, branch |

**Product families:** `DepositProduct` (savings, current, term deposit), `LendingProduct` (personal loan, mortgage, credit line), `CardProduct` (debit, credit, prepaid), `InvestmentProduct` (mutual fund, brokerage), `PaymentProduct` (remittance, UPI/wire).

**Account subtypes mirror product families:** `DepositAccount`, `LoanAccount`, `CardAccount`, `InvestmentAccount`.

### 2.3 Transactions & Events

| Entity | Definition | Key attributes |
|---|---|---|
| `Transaction` | A financial movement affecting an account | txn_id, amount, currency, value_date, booking_date, status |
| `TransactionLeg` | One side of a double-entry movement | debit/credit, account_ref, amount |
| `Event` | A non-monetary lifecycle occurrence | event_type, timestamp, actor |

**Transaction subtypes:** `Payment`, `Transfer`, `Deposit`, `Withdrawal`, `FXTrade`, `Fee`, `InterestAccrual`, `Reversal`, `Chargeback`.

**Event subtypes:** `AccountOpened`, `AccountClosed`, `KYCCompleted`, `LimitChanged`, `CardIssued`, `DisputeRaised`, `ConsentGranted`, `ConsentRevoked`.

### 2.4 Processes & Channels

| Entity | Definition | Key attributes |
|---|---|---|
| `BusinessProcess` | A named end-to-end workflow (BIAN-aligned) | process_id, bian_service_domain, owner, sla |
| `ProcessStep` | An ordered step within a process | step_order, step_type, automation_level |
| `Channel` | Touchpoint where interaction occurs | channel_type, availability |
| `Case` | A long-running work item (dispute, investigation, application) | case_id, status, priority, assigned_to |

**Key processes (BIAN-mapped):** `CustomerOnboarding` / `AccountOpening` (BIAN: Party Lifecycle Mgmt, Savings/Current Account), `KYCVerification` (Party Authentication, Regulatory Compliance), `LoanOrigination` (Consumer Loan), `AMLMonitoring` (Fraud Detection / Financial Crime), `Collections`, `DisputeResolution`, `AccountClosure`, `CreditDecisioning`.

**Channels:** `Branch`, `MobileApp`, `InternetBanking`, `ATM`, `CallCenter`, `RelationshipManager`, `PartnerAPI`, `Agent`.

### 2.5 Risk, Compliance & Documents

| Entity | Definition | Key attributes |
|---|---|---|
| `RegulatoryObligation` | A specific rule the bank must satisfy | regulation (e.g., BCBS 239, AML/CFT, GDPR/DPDP), jurisdiction, effective_date |
| `RiskAssessment` | A scored evaluation attached to a Party/Account/Txn | risk_type (credit/fraud/AML), score, model_version, assessed_at |
| `Document` | Evidence artifact | doc_type (ID proof, address proof, agreement), status, expiry |
| `Consent` | A Party's permission for a data use | purpose, scope, granted_at, revoked_at |
| `Watchlist` / `Sanction` | External screening lists | list_source, entry_ref |

---

## 3. Semantic Plane

This is the layer that makes the system *semantic* rather than a catalog.

| Entity | Definition | Key attributes |
|---|---|---|
| `DataConcept` | A canonical, system-agnostic unit of meaning ("Customer Identifier", "Account Balance", "Date of Birth") | concept_id, name, definition, datatype_class, fibo_uri |
| `BusinessTerm` | A glossary term as used by humans; many terms → one concept | term, definition, steward, synonyms[] |
| `DataDomain` | Top-level grouping for ownership/governance | domain_name, data_owner, steward |
| `DataProduct` | A curated, consumable dataset with an owner and SLA | product_name, owner, refresh_sla, access_policy |
| `Metric` / `KPI` | A defined calculation over concepts | formula, grain, owner ("NPA ratio", "CASA ratio", "Activation rate") |
| `ClassificationTag` | Sensitivity/regulatory labels | PII, PCI, SPI, Confidential/Internal/Public, data_sovereignty |
| `DataQualityRule` | An assertion about a concept's valid values | rule_type (completeness, format, range, referential), threshold |
| `SynonymSet` | Equivalence group for matching | members[], match_method, confidence |

**Standard data domains for a bank:** `Customer`, `Account`, `Product`, `Transaction`, `Risk`, `Compliance`, `ReferenceData` (branches, currencies, rates), `HR`, `Finance/GL`, `Collateral`.

> **The resolution chain:** `Column "cust_id"` —represents→ `DataConcept "Customer Identifier"` —identifies→ `Party (role: Customer)`. Every technical field in the bank should resolve through exactly this chain. Fields that can't resolve are your **dark data backlog** — itself a valuable report.

---

## 4. Technical Plane

### 4.1 Systems & Services

| Entity | Definition | Key attributes |
|---|---|---|
| `System` | A deployed application/platform (core banking, CRM, LOS) | system_id, name, vendor, criticality_tier, environment |
| `Service` | A deployable unit within a system (microservice, batch module) | service_name, repo_url, team_owner, runtime |
| `API` | A published interface contract | api_name, spec_url (OpenAPI), version, auth_scheme |
| `Endpoint` | One operation on an API | method, path, request_schema, response_schema |
| `MessageSchema` | Event/message contract (Avro/Proto/ISO 20022) | schema_id, registry_ref, version |

### 4.2 Data Stores

| Entity | Definition | Key attributes |
|---|---|---|
| `Database` | A database instance/cluster | engine, host_ref, environment |
| `Schema` | Namespace within a database | schema_name |
| `Table` / `View` | Relational object | name, row_estimate, is_view, ddl_hash |
| `Column` | Field within a table | name, datatype, nullable, is_pk, is_fk, sample_profile |
| `Dataset` / `File` | Non-relational data asset (S3 path, feed file) | format, location, partitioning |
| `EventTopic` | Stream/queue | topic_name, broker, retention, schema_ref |

### 4.3 Processing & Consumption

| Entity | Definition | Key attributes |
|---|---|---|
| `Pipeline` | An orchestrated DAG (Airflow, Informatica, Spark) | pipeline_id, schedule, orchestrator |
| `Job` / `Task` | A node within a pipeline | task_type, source_code_ref |
| `MLModel` | A trained model in use | model_id, version, training_dataset_ref, registry_ref |
| `Feature` | A feature-store feature | feature_name, entity_key, freshness |
| `Report` / `Dashboard` | A consumption artifact | tool (Tableau/PowerBI), audience, refresh |

---

## 5. Relationship Taxonomy

### 5.1 Structural (within a plane)

| Edge | Domain → Range | Notes |
|---|---|---|
| `contains` | System→Service, Database→Schema→Table, Pipeline→Job | hierarchy backbone |
| `has_column` | Table→Column | |
| `exposes` | Service→API, API→Endpoint | |
| `has_role` | Party→PartyRole | |
| `instantiates` | Account→Product, Agreement→Product | |
| `step_of` | ProcessStep→BusinessProcess | ordered |

### 5.2 Data Flow (technical plane — the lineage core)

| Edge | Domain → Range | Typical provenance |
|---|---|---|
| `reads_from` | Service/Job→Table/Topic/API | code analysis, query logs |
| `writes_to` | Service/Job→Table/Topic | code analysis, query logs |
| `calls` | Service→Endpoint | code analysis, traces (OpenTelemetry) |
| `produces` / `consumes` | Service→EventTopic | schema registry, code |
| `derives_from` | Column→Column, Dataset→Dataset | SQL parsing, OpenLineage |
| `feeds` | Table/Dataset→Report/MLModel | BI metadata, model registry |
| `trained_on` | MLModel→Dataset | model registry |

### 5.3 Cross-Plane (the bridges — highest value)

| Edge | Domain → Range | Meaning |
|---|---|---|
| `represents` | Column/Field→DataConcept | the resolution chain start |
| `concept_of` | DataConcept→BusinessEntity | "Customer Identifier" → Party |
| `realizes` | Service/API→BusinessProcess/ProcessStep | which tech implements which process |
| `belongs_to_domain` | Table/DataProduct/Concept→DataDomain | governance routing |
| `classified_as` | Column/Dataset→ClassificationTag | PII/PCI propagation |
| `evidences` | Table/Report→RegulatoryObligation | compliance traceability (BCBS 239) |
| `governed_by` | DataConcept→DataQualityRule | |
| `system_of_record_for` | System→DataConcept/DataDomain | exactly one golden source per concept |

### 5.4 Semantic

| Edge | Meaning |
|---|---|
| `synonym_of` | term/field equivalence (carries match_method + confidence) |
| `is_a` | subtype (DepositAccount is_a Account) |
| `part_of` | composition |
| `related_to` | weak association (embedding similarity above threshold) |

### 5.5 Edge Metadata (mandatory on every edge)

```json
{
  "confidence_tier": "T1 | T2 | T3",
  "confidence_score": 0.0-1.0,
  "provenance": "fk_constraint | openapi_spec | query_log | sql_parse | code_llm | embedding_sim | human_curated",
  "extracted_at": "timestamp",
  "extractor_version": "harvester@x.y",
  "verified_by": "optional human steward"
}
```

**Tier definitions:**
- **T1 Deterministic (0.95–1.0):** FK constraints, declared OpenAPI schemas, schema-registry contracts, orchestrator DAG edges, human-curated.
- **T2 Heuristic (0.7–0.95):** query-log joins, naming-convention matches, SQL lineage parsing, trace data.
- **T3 AI-Inferred (0.3–0.7):** LLM reading of code/docs, embedding similarity, description matching. *Always queued for human verification; promotion to T1 on steward approval.*

---

## 6. Worked Example: Account Opening

The flagship query — *"What does Account Opening need and touch?"* — resolves like this:

```
(BusinessProcess: AccountOpening)
 ├─ step_of⁻¹ → [CaptureApplication, KYCVerification, RiskScoring,
 │               ProductSelection, AccountProvisioning, CardIssuance, Notification]
 ├─ realizes⁻¹ →
 │    (Service: onboarding-api)        — exposes → POST /v2/applications
 │    (Service: kyc-orchestrator)      — calls → VendorAPI: id-verification
 │    (Service: risk-scoring-svc)      — uses → (MLModel: onboard_risk_v7)
 │    (Service: core-banking-adapter)  — calls → CBS SOAP: createAccount
 │    (Pipeline: nightly_aml_screen)   — reads_from → cust_master, watchlist_feed
 ├─ data touched (via realizes → reads/writes → represents):
 │    cust_master.cust_id        → Customer Identifier   [PII]
 │    cust_master.dob            → Date of Birth          [PII]
 │    kyc_docs.doc_hash          → Identity Document      [SPI]
 │    risk_score.score           → Onboarding Risk Score
 │    acct_master.acct_no        → Account Number         [Confidential]
 ├─ evidences → (RegulatoryObligation: KYC/AML-CFT, DPDP-Consent)
 └─ system_of_record: CBS for Account, CRM for Party, DMS for Document
```

Reverse traversal gives **impact analysis** for free: *"if `cust_master.dob` changes datatype, what breaks?"* → every Service/Pipeline/Report reachable via `reads_from`/`derives_from`, ranked by criticality_tier.

---

## 7. Implementation Notes

**Property graph (recommended start):** Neo4j / Neptune / your NetworkX prototype. Entity types above become node labels; section 5 edges become relationship types; edge metadata as relationship properties. RDF/OWL is the alternative if you want direct FIBO imports and SHACL validation — heavier, but stronger for regulator-facing semantics. A pragmatic middle path: property graph for runtime, with FIBO URIs stored as node properties for crosswalk.

**ID strategy:** URN scheme `urn:sdl:{plane}:{type}:{source_system}:{native_id}` — e.g., `urn:sdl:tech:column:cbs:cust_master.cust_id`. Deterministic IDs make re-harvesting idempotent.

**Ingest priority (highest signal per effort):**
1. DB catalogs + FK constraints (T1, cheap)
2. OpenAPI specs + schema registry (T1, cheap)
3. Orchestrator DAGs / OpenLineage (T1–T2)
4. Query logs → join inference (T2)
5. LLM code analysis for reads/writes/calls (T3, the differentiator)
6. Glossary + steward curation of DataConcepts (human, ongoing)

**Versioning:** snapshot the graph per harvest run; concept definitions are append-only with effective dating — regulators ask "what did this mean in March."

---

## 8. Standards Crosswalk

| Ontology area | External standard | What to reuse |
|---|---|---|
| Party, Agreement, Product | **FIBO** (FND, BE, FBC modules) | class definitions + URIs |
| Process & capability map | **BIAN** Service Landscape | service domain names as `bian_service_domain` attribute |
| Payments & messages | **ISO 20022** | message component → DataConcept mapping |
| Lineage events | **OpenLineage** | harvester event format |
| Catalog interop | **DCAT / open metadata (DataHub, OpenMetadata)** | export format for coexistence with existing catalogs |

---

## 9. What to Build First

Phase 1 scope that proves the ontology: **one process (Account Opening), two systems (CBS + onboarding service), full resolution chain.** Harvest DB catalog + OpenAPI spec (T1 edges), hand-curate ~30 DataConcepts for the Customer/Account domains, run one LLM code-analysis pass (T3 edges), and demo the forward query ("what does account opening touch") plus the reverse query ("what breaks if X changes"). Everything industry-leading about this platform is visible in that single demo.
