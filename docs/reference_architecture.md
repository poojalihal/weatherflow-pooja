# WeatherFlow reference architecture

flowchart LR
    subgraph SOURCES["DATA SOURCES"]
        A["WeatherAPI"]
        B["OpenWeatherMap"]
        C["Simulated Weather Stations"]
    end

    subgraph INGEST["INGESTION - E"]
        D["Python API Scripts<br/>Weather Data Producer"]
    end

    subgraph STREAM["MESSAGE BROKER"]
        E[("Kafka Topic<br/>weather-raw-data")]
        F["Kafka Consumer"]
    end

    subgraph PROCESS["PROCESSING - T"]
        G["Apache Spark<br/>Batch and Streaming"]
        H["Weather Metrics<br/>Heat Index and Severity"]
    end

    subgraph STORAGE["STORAGE - L"]
        I[("Data Lake<br/>Raw Zone")]
        J[("Data Lake<br/>Processed Zone")]
        K[("PostgreSQL<br/>Airflow Metadata")]
    end

    subgraph ORCHESTRATION["ORCHESTRATION"]
        L["Apache Airflow<br/>Scheduling and Monitoring"]
    end

    subgraph SERVING["SERVING"]
        M["Reports<br/>CSV / HTML / PNG"]
        N["Interactive Dashboard<br/>Flask / Dash"]
        O["Weather Charts<br/>ApexCharts.js"]
    end

    A --> D
    B --> D
    C --> D

    D --> E
    D --> I
    E --> F
    F --> G
    G --> H
    H --> J

    J --> M
    J --> N
    M --> N
    N --> O

    L -.-> D
    L -.-> F
    L -.-> G
    L -.-> M
    L -.-> K
