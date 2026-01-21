# Fund Portfolio Intelligence System

A production-ready AI-powered system for mutual fund portfolio analysis, combining SQL analytics, Neo4j graph database, and LLM-based data extraction from PDF factsheets.

##  Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Query Interface                         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │   Query Router       │
                    │   (DSPy-based)       │
                    └───────┬──────┬───────┘
                            │      │
              ┌─────────────┘      └─────────────┐
              │                                   │
    ┌─────────▼────────┐              ┌─────────▼──────────┐
    │   SQL Agent      │              │  GraphDB Agent     │
    │  (LangGraph)     │              │  (Neo4j Cypher)    │
    └─────────┬────────┘              └─────────┬──────────┘
              │                                   │
    ┌─────────▼────────┐              ┌─────────▼──────────┐
    │  SQLite DB       │              │   Neo4j Graph      │
    │  - Fund metrics  │              │  - Holdings        │
    │  - Performance   │              │  - Relationships   │
    │  - Benchmarks    │              │  - Temporal data   │
    └──────────────────┘              └────────────────────┘
              ▲                                   ▲
              │                                   │
              └───────────┬───────────────────────┘
                          │
              ┌───────────▼──────────┐
              │  PDF Extraction       │
              │  Pipeline             │
              │  - Azure Doc Intel   │
              │  - LLM Cleaning      │
              │  - ISIN Mapping      │
              └──────────────────────┘
```

## Key Features

### 1. **Intelligent Query Routing**
- Automatic classification of queries to SQL or Graph database
- DSPy-based reasoning for optimal data source selection
- Support for hybrid queries combining both databases

### 2. **PDF Portfolio Extraction**
- Azure Document Intelligence for table extraction
- LLM-powered data cleaning and normalization
- Automatic ISIN mapping for securities
- Support for multiple asset classes (Equity, Debt, Money Market)

### 3. **Graph-Based Analysis**
- Neo4j temporal graph for portfolio holdings
- Historical tracking of fund compositions
- Portfolio overlap analysis
- AMC positioning insights

### 4. **SQL Analytics**
- Fund performance screening
- Multi-factor ranking system
- Benchmark comparison
- Human-in-the-loop approval for sensitive queries

## 📁 Project Structure

```
fund-portfolio-intelligence/
│
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py          # Azure Document Intelligence integration
│   │   ├── data_cleaner.py           # LLM-based table normalization
│   │   └── holding_classifier.py     # Asset classification logic
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── query_router.py           # DSPy query routing
│   │   ├── sql_agent.py              # LangGraph SQL agent
│   │   └── graph_agent.py            # Neo4j graph agent
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── neo4j_manager.py          # Neo4j connection & operations
│   │   └── sql_tools.py              # SQL database tools
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py                 # Configuration management
│       └── isin_mapper.py            # ISIN mapping utilities
│
├── config/
│   ├── config.yaml                   # Main configuration
│   └── .env.example                  # Environment variables template
│
├── data/
│   ├── raw/                          # Raw PDF factsheets
│   ├── processed/                    # Processed JSON outputs
│   └── master/                       # Master data (ISIN mappings)
│
├── docs/
│   ├── architecture.md               # Detailed architecture
│   ├── data_model.md                 # Data models and schemas
│   └── api_reference.md              # API documentation
│
├── scripts/
│   ├── setup_database.py             # Database initialization
│   ├── batch_process_pdfs.py         # Batch PDF processing
│   └── load_neo4j.py                 # Neo4j data loading
│
├── main.py                           # Main application entry point
├── requirements.txt                  # Python dependencies
├── .env                              # Environment variables (gitignored)
├── .gitignore
└── README.md
```

##  Quick Start

### Prerequisites

- Python 3.9+
- Neo4j Database (v5.x recommended)
- Azure Document Intelligence account
- Groq API key (for LLM operations)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fund-portfolio-intelligence
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp config/.env.example .env
   # Edit .env with your credentials
   ```

5. **Initialize databases**
   ```bash
   python scripts/setup_database.py
   ```

### Configuration

Edit `.env` file with your credentials:

```env
# Azure Document Intelligence
AZURE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_KEY=your-azure-key

# Groq API
GROQ_API_KEY=your-groq-api-key

# Neo4j Database
NEO4J_URL=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-neo4j-password

# SQLite Database
SQLITE_DB_PATH=./data/whitelist_db.db

# Master Data
ISIN_MAPPING_PATH=./data/master/MASTERDATA.csv
```

## 💻Usage

### 1. Process PDF Factsheets

```python
from src.core.pdf_extractor import FundPortfolioProcessor

processor = FundPortfolioProcessor()
results = processor.process_pdf("path/to/factsheet.pdf")
```

### 2. Query Fund Data

```python
from main import FundIntelligenceSystem

system = FundIntelligenceSystem()

# Automatic routing to appropriate database
result = system.query("Which AMC has the highest position in HDFC Bank?")
print(result)
```

### 3. Screen Funds

```python
# The system handles human-in-the-loop approval for screening
result = system.query(
    "Screen all Large cap funds with weights: 0.5 for 3-month returns, "
    "0.3 for 1-year alpha, and 0.2 for 1-year beta"
)
```

##  Example Queries

### SQL Queries (Performance Analytics)
- "List top 5 midcap funds based on last 6 months returns"
- "Which Flexicap funds beat Nifty 500 in the last 1 year?"
- "Compare alpha and beta of focused funds"

### Graph Queries (Portfolio Analysis)
- "Which AMC has the highest position in HDFC Bank?"
- "Show portfolio overlap between Fund A and Fund B"
- "List all stocks held by DSP Focused Fund"
- "Which focused fund holds Money Market Instruments?"

### Hybrid Queries
- "Find top performing funds that hold HDFC Bank"
- "Screen funds with good returns and show their top holdings"

## 🔧 Advanced Features

### Human-in-the-Loop Approval

The system implements middleware for sensitive operations:

```python
# Screening operations require user approval
decision = get_user_decision(action)
# User can approve/reject before execution
```

### Asset Classification

Supports comprehensive asset class taxonomy:
- **Equity & Equity Related**: Indian Equity, Foreign Equity, REITs, ETFs
- **Corporate Debt**: Bonds, NCDs, Convertible Debentures
- **Government Securities**: T-Bills, State Bonds
- **Money Market**: CDs, Commercial Paper, TREPS

### ISIN Mapping

Automatic mapping of company names to ISIN codes:
- Fuzzy matching for name variations
- Market cap enrichment
- Support for international securities

##  Data Models

### Neo4j Graph Schema

```cypher
(:Fund)-[:LATEST_SNAPSHOT]->(:MonthlySnapshot)-[:HOLDS {weight}]->(:Instrument)
(:Fund)-[:CURRENT_HOLDINGS {weight}]->(:Instrument)
```

### SQL Tables

- `LARGE_CAP_FUNDS`: Large cap fund performance metrics
- `MID_CAP_FUNDS`: Mid cap fund performance metrics
- `FLEXI_CAP_FUNDS`: Flexi cap fund performance metrics
- `SMALL_CAP_FUNDS`: Small cap fund performance metrics

## Roadmap

- [ ] Real-time market data integration
- [ ] Multi-language support for factsheets
- [ ] Advanced portfolio optimization
- [ ] RESTful API development
- [ ] Web dashboard interface
- [ ] Automated report generation
