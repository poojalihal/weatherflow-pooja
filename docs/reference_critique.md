
# WeatherFlow Reference Architecture Critique

## 1. Component Table

| Component | Tool used | What it does in this project | Batch or streaming? |
|---|---|---|---|
| Data source | WeatherAPI, OpenWeatherMap and simulated weather station data | Provides weather information from multiple sources through APIs and simulated inputs. | API polling / batch ingestion |
| Message broker | Apache Kafka | Receives weather messages from producers and distributes them to consumers through Kafka topics. | Streaming |
| Processing | Apache Spark | Processes weather data, performs transformations and calculates metrics such as heat index and weather severity. | Both batch and streaming |
| Orchestration | Apache Airflow | Schedules pipeline execution, monitors components and handles retries and failures. | Scheduled batch / triggered workflows |
| Storage | File-based data lake (raw and processed zones); PostgreSQL for Airflow metadata | Preserves raw weather data and processed outputs. PostgreSQL stores Airflow's workflow metadata. | Batch-oriented file storage; metadata database |
| Serving | Flask/Dash dashboard, ApexCharts.js | Displays weather information through interactive charts, filters and visualisations. | Dashboard serving; refresh frequency needs verification |
| Packaging | Docker Compose | Configures and runs the pipeline services together in containers. | Not applicable |


## 2. Architecture Critique

The reference architecture has several strengths. It separates data ingestion, messaging, processing, orchestration, storage and visualisation, making the responsibilities of each stage clear. Kafka provides a way to distribute weather events between producers and consumers, while Spark supports both batch processing and streaming analytics. Airflow adds scheduling, monitoring and retry capabilities. The raw and processed data zones also provide a useful separation between original source data and transformed outputs. These choices demonstrate concepts used in larger data platforms.

However, the repository has several risks. First, the WeatherAPI key is exposed directly in README.md under Setup and Installation and is repeated in IMPLEMENTATION.md under Initial Setup. A public repository can expose this credential to others. The key should be revoked and replaced, then loaded from an environment variable or an untracked .env file; documentation should contain only a placeholder.

Second, the dashboard documentation is inconsistent. README.md describes Flask in its technology list but also instructs users to run streamlit_dashboard.py on port 8501. IMPLEMENTATION.md describes a Dash/Flask dashboard at dashboard/app.py. A new developer cannot easily tell which application is authoritative. The documentation should be reconciled with the actual code.

Third, the architecture may be unnecessarily complex for a feed covering only five cities with hourly updates. Kafka and Spark add infrastructure and operational overhead when a scheduled Python job could likely collect and transform this small volume. Finally, although IMPLEMENTATION.md describes monitoring commands and the repository contains test_weather_api.py, the guides do not clearly define automated test execution, data-quality checks or alerting when scheduled collection fails. The team should document these checks and add failure notifications.

For a five-city hourly feed, API access, Python extraction, raw file storage, basic transformation, a database and a simple dashboard are essential. A scheduler is useful to run the job hourly. Docker may help with reproducible deployment but is optional at this scale. Kafka and Spark are likely overkill unless the system later needs high event throughput, multiple consumers, near-real-time processing or substantial scaling. Airflow may also be more than necessary; a simpler scheduler could initially meet the requirement. The design should start with the simplest reliable architecture and add distributed components only when measurable needs justify them.

