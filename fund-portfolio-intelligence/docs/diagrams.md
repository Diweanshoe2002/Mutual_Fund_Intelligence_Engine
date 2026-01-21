# System Architecture Diagram

## High-Level System Architecture

```mermaid
graph TB
    subgraph "User Interface"
        CLI[CLI Interface]
        Future[Future: Web Dashboard]
    end
    
    subgraph "Intelligence Layer"
        Router[Query Router<br/>DSPy]
        Planner[Graph Planner<br/>DSPy]
    end
    
    subgraph "Agent Layer"
        SQLAgent[SQL Agent<br/>LangGraph]
        GraphAgent[Graph Agent<br/>LangChain]
    end
    
    subgraph "Tools Layer"
        SQLTools[SQL Toolkit]
        Screener[Fund Screener]
        Benchmark[Benchmark Fetcher]
    end
    
    subgraph "Data Processing"
        PDFExtract[PDF Extractor<br/>Azure Document Intelligence]
        Cleaner[Data Cleaner<br/>LangGraph]
        Classifier[Asset Classifier<br/>DSPy]
        ISINMap[ISIN Mapper]
    end
    
    subgraph "Data Storage"
        SQLite[(SQLite<br/>Performance Data)]
        Neo4j[(Neo4j<br/>Holdings Graph)]
        Master[(Master Data<br/>ISIN Mappings)]
    end
    
    CLI --> Router
    Future -.-> Router
    
    Router -->|SQL Route| SQLAgent
    Router -->|Graph Route| Planner
    
    Planner --> GraphAgent
    
    SQLAgent --> SQLTools
    SQLAgent --> Screener
    SQLAgent --> Benchmark
    
    SQLTools --> SQLite
    Screener --> SQLite
    GraphAgent --> Neo4j
    
    PDFExtract --> Cleaner
    Cleaner --> Classifier
    Classifier --> ISINMap
    ISINMap --> Master
    ISINMap --> Neo4j
    
    style Router fill:#e1f5ff
    style SQLAgent fill:#fff3e0
    style GraphAgent fill:#f3e5f5
    style Neo4j fill:#c8e6c9
    style SQLite fill:#ffccbc
```

## Query Routing Flow

```mermaid
flowchart TD
    Start([User Query]) --> Router{Query Router<br/>DSPy Reasoning}
    
    Router -->|Performance Metrics| SQL[SQL Route]
    Router -->|Holdings/Relationships| Graph[Graph Route]
    
    SQL --> SQLAgent[SQL Agent]
    SQLAgent --> Tools{Tool Selection}
    
    Tools --> QueryTool[SQL Query Tool]
    Tools --> ScreenTool[Screener Tool]
    Tools --> BenchTool[Benchmark Tool]
    
    QueryTool --> SQLExec[(Execute SQL)]
    ScreenTool --> Approval{Human Approval?}
    BenchTool --> YFinance[Yahoo Finance API]
    
    Approval -->|Approved| SQLExec
    Approval -->|Rejected| End1([Cancel])
    
    Graph --> Planner[Graph Planner]
    Planner --> Aligned[Schema-Aligned Query]
    Aligned --> CypherGen[Cypher Generator]
    CypherGen --> Neo4jExec[(Execute Cypher)]
    
    SQLExec --> Result1[SQL Result]
    YFinance --> Result1
    Neo4jExec --> Result2[Graph Result]
    
    Result1 --> Format1[Format Response]
    Result2 --> Format2[Format Response]
    
    Format1 --> End2([Return to User])
    Format2 --> End2
    
    style Router fill:#e1f5ff
    style SQLAgent fill:#fff3e0
    style Planner fill:#f3e5f5
    style Approval fill:#ffeb3b
```

## PDF Processing Pipeline

```mermaid
flowchart TD
    Start([PDF Factsheet]) --> Azure[Azure Document<br/>Intelligence]
    
    Azure --> Tables[Extract Tables]
    Azure --> Pages[Detect Pages]
    Azure --> Text[Extract Text]
    
    Tables --> Detect{Detect Fund Name}
    Pages --> Detect
    Text --> Detect
    
    Detect --> Merge[Merge Consecutive<br/>Tables]
    
    Merge --> Markdown[Convert to<br/>Markdown]
    
    Markdown --> LLM[LLM Cleaning<br/>TableCleanerCoT]
    
    LLM --> Classify[Asset Classification]
    
    Classify --> Groups{Asset Groups}
    
    Groups --> Equity[Equity & Equity<br/>Related]
    Groups --> Debt[Corporate Debt]
    Groups --> Govt[Government<br/>Securities]
    Groups --> Money[Money Market]
    Groups --> Other[Other]
    
    Equity --> ISIN{ISIN Mapping}
    Debt --> Skip[Skip ISIN]
    Govt --> Skip
    Money --> Skip
    Other --> Skip
    
    ISIN --> Master[(Master Data<br/>ISIN CSV)]
    Master --> Enrich[Enrich with<br/>Market Cap]
    
    Enrich --> JSON[Structured JSON]
    Skip --> JSON
    
    JSON --> Save[(Save to File)]
    JSON --> Neo4j[(Load to Neo4j)]
    
    Neo4j --> Instruments[Create Instruments]
    Neo4j --> Snapshot[Create Snapshot]
    Neo4j --> Holdings[Create Holdings]
    Neo4j --> Current[Update Current<br/>Holdings]
    
    Save --> End([Complete])
    Current --> End
    
    style Azure fill:#0078d4
    style LLM fill:#e1f5ff
    style Neo4j fill:#c8e6c9
    style ISIN fill:#fff3e0
```

## Neo4j Graph Data Model

```mermaid
graph LR
    subgraph "Funds"
        F1[Fund<br/>fund_id: 9109<br/>fund_name: DSP Focused<br/>amc: DSP]
        F2[Fund<br/>fund_id: 9110<br/>fund_name: ICICI Focused<br/>amc: ICICI]
    end
    
    subgraph "Snapshots"
        S1[MonthlySnapshot<br/>snapshot_id: 202501<br/>year: 2025<br/>month: 1<br/>total_aum: 1000]
        S2[MonthlySnapshot<br/>snapshot_id: 202412<br/>year: 2024<br/>month: 12<br/>total_aum: 950]
    end
    
    subgraph "Instruments"
        I1[Instrument<br/>instrument_id: INE040A01034<br/>name: HDFC Bank<br/>asset_class: EQUITY<br/>sub_type: Indian Equity]
        I2[Instrument<br/>instrument_id: INE090A01021<br/>name: ICICI Bank<br/>asset_class: EQUITY<br/>sub_type: Indian Equity]
    end
    
    F1 -->|LATEST_SNAPSHOT| S1
    F1 -->|CURRENT_HOLDINGS<br/>weight: 9.18| I1
    F1 -->|CURRENT_HOLDINGS<br/>weight: 7.0| I2
    
    S1 -->|HOLDS<br/>weight: 9.18| I1
    S1 -->|HOLDS<br/>weight: 7.0| I2
    
    F2 -->|CURRENT_HOLDINGS<br/>weight: 8.5| I1
    
    style F1 fill:#fff3e0
    style F2 fill:#fff3e0
    style S1 fill:#e1f5ff
    style S2 fill:#e1f5ff
    style I1 fill:#c8e6c9
    style I2 fill:#c8e6c9
```

## Component Dependencies

```mermaid
graph TD
    subgraph "Configuration"
        Config[config.py]
        Env[.env]
    end
    
    subgraph "Core Modules"
        PDF[pdf_extractor.py]
        Cleaner[data_cleaner.py]
        Classifier[holding_classifier.py]
    end
    
    subgraph "Database"
        Neo4jMgr[neo4j_manager.py]
        SQLTools[sql_tools.py]
    end
    
    subgraph "Agents"
        Router[query_router.py]
        Main[main.py]
    end
    
    Env --> Config
    
    Config --> PDF
    Config --> Cleaner
    Config --> Classifier
    Config --> Neo4jMgr
    Config --> SQLTools
    Config --> Router
    Config --> Main
    
    Classifier --> Cleaner
    PDF --> Cleaner
    Cleaner --> Neo4jMgr
    
    Router --> Main
    Neo4jMgr --> Main
    SQLTools --> Main
    
    style Config fill:#e1f5ff
    style Main fill:#ffeb3b
```

## Data Transformation Flow

```mermaid
flowchart LR
    subgraph "Input"
        Raw[Raw OCR Table<br/>Markdown Format]
    end
    
    subgraph "Processing"
        LLM[LLM Normalization]
        Class[Classification]
        Map[ISIN Mapping]
    end
    
    subgraph "Output"
        JSON[Structured JSON<br/>fund_name<br/>name<br/>stock_id<br/>weights<br/>asset_class<br/>sub_type<br/>market_cap]
    end
    
    Raw --> LLM
    LLM --> Class
    Class --> Map
    Map --> JSON
    
    style Raw fill:#ffccbc
    style JSON fill:#c8e6c9
```
