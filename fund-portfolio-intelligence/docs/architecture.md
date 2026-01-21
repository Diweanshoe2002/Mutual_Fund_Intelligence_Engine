# System Architecture

## Overview

The Fund Portfolio Intelligence System is a hybrid AI-powered analytics platform combining SQL analytics with graph database traversal for comprehensive mutual fund portfolio analysis.

## Architecture Layers

### 1. Presentation Layer
- **Interactive CLI**: Command-line interface for query input
- **Future**: REST API endpoints, Web dashboard

### 2. Intelligence Layer

#### Query Router (DSPy-based)
- **Purpose**: Intelligently routes queries to appropriate database
- **Technology**: DSPy with Groq LLM
- **Decision Logic**:
  - **SQL Route**: Performance metrics, screening, benchmarks, rankings
  - **Graph Route**: Holdings, relationships, portfolio overlap, AMC analysis

#### Graph Query Planner
- **Purpose**: Aligns user questions with Neo4j schema
- **Output**: Refined queries optimized for graph traversal

### 3. Agent Layer

#### SQL Agent (LangGraph)
- **Framework**: LangChain + LangGraph
- **Capabilities**:
  - Dynamic SQL query generation
  - Multi-tool orchestration
  - Human-in-the-loop approval for sensitive operations
- **Tools**:
  - SQL database toolkit (query, schema inspection)
  - Custom mutual fund screener
  - Benchmark data fetcher (Yahoo Finance)

#### Graph Agent
- **Framework**: LangChain GraphCypherQAChain
- **Capabilities**:
  - Cypher query generation
  - Graph traversal optimization
  - Relationship analysis

### 4. Data Processing Layer

#### PDF Extraction Pipeline
```
PDF Factsheet
    ↓
Azure Document Intelligence (OCR)
    ↓
Table Extraction & Page Detection
    ↓
LLM-based Data Cleaning (DSPy)
    ↓
Asset Classification & Normalization
    ↓
ISIN Mapping
    ↓
Structured JSON Output
```

**Components**:
- **PDFTableExtractor**: Azure Document Intelligence integration
- **DataCleaningAgent**: LangGraph workflow for table normalization
- **TableCleanerCoT**: DSPy chain-of-thought classifier
- **ISINMapper**: Company name to ISIN resolution

### 5. Data Storage Layer

#### SQL Database (SQLite)
**Schema**:
- `LARGE_CAP_FUNDS`
- `MID_CAP_FUNDS`
- `FLEXI_CAP_FUNDS`
- `SMALL_CAP_FUNDS`

**Columns**: Fund_Name, Returns_3m, Returns_6m, Returns_1y, Alpha_1y, Beta_1y, Sharpe_1y, etc.

#### Graph Database (Neo4j)
**Node Types**:
- `Fund`: Mutual fund entities
- `Instrument`: Securities (stocks, bonds, etc.)
- `MonthlySnapshot`: Point-in-time portfolio state

**Relationships**:
- `Fund -[:LATEST_SNAPSHOT]-> MonthlySnapshot`
- `Fund -[:CURRENT_HOLDINGS {weight}]-> Instrument`
- `MonthlySnapshot -[:HOLDS {weight}]-> Instrument`

**Temporal Design**:
- Snapshots enable historical analysis
- Current holdings enable fast queries
- Weight property stores allocation percentage

### 6. Configuration Layer

**Centralized Config Management**:
- Pydantic models for type safety
- Environment variable loading
- Separate configs for Azure, Groq, Neo4j, SQLite
- Path management for data files

## Data Flow Diagrams

### Query Execution Flow

```
User Query
    ↓
Query Router (DSPy)
    ├─→ SQL Route
    │   ├─→ SQL Agent (LangGraph)
    │   │   ├─→ Query Generation
    │   │   ├─→ Tool Selection
    │   │   ├─→ Human Approval (if needed)
    │   │   └─→ SQLite Execution
    │   └─→ Result Formatting
    │
    └─→ Graph Route
        ├─→ Graph Planner (DSPy)
        ├─→ Schema Alignment
        ├─→ Graph Agent
        │   ├─→ Cypher Generation
        │   └─→ Neo4j Execution
        └─→ Result Formatting
```

### PDF Processing Flow

```
PDF Upload
    ↓
Azure Document Intelligence
    ├─→ Page Analysis
    ├─→ Table Detection
    └─→ Text Extraction
    ↓
Fund Name Detection
    ├─→ Keyword Search ("fund")
    └─→ Context Analysis
    ↓
Table Merging
    ├─→ Header Matching
    └─→ Concatenation
    ↓
LLM Cleaning (DSPy)
    ├─→ Asset Classification
    ├─→ Data Normalization
    └─→ JSON Structuring
    ↓
ISIN Mapping
    ├─→ Name Normalization
    ├─→ Fuzzy Matching
    └─→ Market Cap Enrichment
    ↓
Neo4j Loading
    ├─→ Instrument Creation
    ├─→ Snapshot Creation
    ├─→ Relationship Building
    └─→ Current Holdings Update
```

## Technology Stack

### AI/ML Frameworks
- **LangChain**: Agent orchestration
- **LangGraph**: Workflow management
- **DSPy**: Structured LLM operations

### LLM Providers
- **Groq**: Fast inference
- **Models**: Moonshot Kimi K2, GPT-OSS-120B

### Azure Services
- **Document Intelligence**: OCR and table extraction

### Databases
- **Neo4j**: Graph database for relationships
- **SQLite**: Relational database for analytics

### Data Processing
- **Pandas**: Data manipulation
- **PyYFINANCE**: Market data

### Configuration
- **Pydantic**: Type-safe configuration
- **python-dotenv**: Environment management

## Scalability Considerations

### Current Design
- Single-threaded query execution
- In-memory checkpointing
- Local SQLite database

### Production Recommendations

1. **Database Scaling**
   - PostgreSQL/MySQL for SQL layer
   - Neo4j cluster for high availability
   - Redis for caching

2. **Processing Scaling**
   - Celery for async PDF processing
   - Message queue (RabbitMQ/Kafka)
   - Distributed task execution

3. **API Layer**
   - FastAPI REST endpoints
   - WebSocket for real-time updates
   - JWT authentication

4. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - ELK stack for logs

## Security Architecture

### API Key Management
- Environment variables (never in code)
- Separate configs per environment
- Rotation policies

### Database Security
- Encrypted connections (TLS/SSL)
- Credential rotation
- Least privilege access

### Data Privacy
- PII handling policies
- Audit logging
- GDPR compliance considerations

## Performance Optimization

### Query Optimization
- Neo4j index creation on instrument_id, fund_id
- SQL index on Fund_Name, Returns columns
- Query result caching

### LLM Optimization
- Batch processing for multiple PDFs
- Response caching for common patterns
- Temperature tuning per use case

### Data Processing
- Parallel PDF processing
- Chunked data loading
- Stream processing for large files

## Extension Points

### Adding New Data Sources
1. Create new tool in `sql_tools.py`
2. Register with toolkit
3. Update agent system prompt

### Adding New LLM Providers
1. Add config in `config.py`
2. Update initialization in agents
3. Test compatibility

### Adding New Query Types
1. Update router signature
2. Add route option
3. Implement execution path

## Deployment Architecture

### Development
- Local SQLite
- Local Neo4j instance
- Environment-based config

### Staging
- Cloud-hosted databases
- Separate API keys
- Integration testing

### Production
- Multi-region deployment
- Load balancing
- Auto-scaling
- Disaster recovery

## Monitoring & Observability

### Metrics
- Query latency
- LLM token usage
- Database query performance
- Error rates

### Logging
- Structured logging (JSON)
- Log levels per component
- Centralized aggregation

### Alerting
- Query failures
- Database connectivity
- API rate limits
- Unusual patterns
