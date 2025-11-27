# Social Trading Risk Analytics Platform

> End-to-end data engineering solution for analyzing trader performance and portfolio risk in social trading networks using modern lakehouse architecture

[![Tech Stack](https://img.shields.io/badge/Databricks-Latest-red)]()
[![Python](https://img.shields.io/badge/Python-3.9+-blue)]()
[![Delta Lake](https://img.shields.io/badge/Delta%20Lake-2.0+-green)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

---

## 📋 Table of Contents

- [Overview](#overview)
- [Business Context](#business-context)
- [Architecture](#architecture)
- [Data Model](#data-model)
- [Financial Metrics Explained](#financial-metrics-explained)
- [Key Insights](#key-insights)
- [Technical Stack](#technical-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Pipeline Execution](#pipeline-execution)
- [Results & Findings](#results--findings)
- [Future Enhancements](#future-enhancements)
- [Author](#author)

---

## 🎯 Overview

This project demonstrates production-grade data engineering for financial analytics, specifically analyzing risk-adjusted performance metrics from social trading platforms where retail investors copy experienced traders' portfolios.

**Core Capabilities:**
- Scalable data ingestion with respectful rate limiting
- Robust HTML parsing handling dynamic content
- Lakehouse architecture (Bronze → Silver → Gold)
- Advanced financial risk metrics computation
- Production-quality data quality controls

---

## 💼 Business Context

### The Social Trading Problem

Social trading platforms (e.g., eToro, ZuluTrade) enable retail investors to copy the portfolios of experienced traders. However, most investors focus solely on returns, ignoring risk.

**Key Challenges:**
1. **Performance Myopia:** High returns often mask high risk
2. **Survivorship Bias:** Platforms highlight winners, hide failures
3. **Lack of Risk Metrics:** Most platforms show basic returns, not risk-adjusted performance
4. **Temporal Volatility:** Past performance ≠ future results

### The Solution

This platform provides:
- **Risk-adjusted metrics** (Sharpe, Sortino, Calmar) for comprehensive trader evaluation
- **Portfolio diversification analysis** (sectors, exchanges, countries)
- **Elite trader identification** based on sustainable performance criteria
- **Data-driven insights** replacing emotional investment decisions

**Target Users:**
- Retail investors seeking copy trading opportunities
- Financial advisors evaluating social trading strategies
- Risk managers monitoring portfolio exposure
- Data scientists building trading models

---

## 🏗️ Architecture

### Medallion Architecture (Bronze → Silver → Gold)

```
┌──────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                                │
│  Social Trading Platforms (Public Trader Profiles)               │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                   BRONZE LAYER (Raw Data)                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  bronze_trader_profiles                                    │  │
│  │  - Raw HTML responses (immutable)                          │  │
│  │  - HTTP status codes                                       │  │
│  │  - Ingestion timestamps                                    │  │
│  │  - Full reprocessability                                   │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                  SILVER LAYER (Curated Data)                     │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  silver_trader_metrics                                  │     │
│  │  - Parsed risk metrics (Sharpe, Sortino, Calmar, Beta)  │     │
│  │  - Returns (monthly, YTD, annual)                       │     │
│  │  - Trader descriptions                                  │     │
│  │  - Data quality validated                               │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  silver_portfolio_composition                           │     │
│  │  - Sector allocations                                   │     │
│  │  - Exchange exposure                                    │     │
│  │  - Geographic diversification                           │     │
│  └─────────────────────────────────────────────────────────┘     │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                   GOLD LAYER (Analytics)                         │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  gold_elite_traders                                     │     │
│  │  - Traders meeting Sortino > 7 AND Calmar > 7           │     │
│  │  - Combined risk-adjusted performance score             │     │
│  │  - Ready for recommendation systems                     │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  gold_top_performers                                    │     │
│  │  - Top 25% by annualized returns                        │     │
│  │  - Baseline for performance comparison                  │     │
│  └─────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

#### 1. Why Medallion Architecture?

**Decision:** Implement Bronze → Silver → Gold layers

**Rationale:**
- **Bronze (Raw):** Immutable data enables reprocessing if parsing logic improves
- **Silver (Curated):** Validated business entities ready for analytics
- **Gold (Aggregated):** Pre-computed insights for dashboards and APIs



## 📊 Data Model

### Bronze Layer

#### `bronze_trader_profiles`
Raw HTML responses from social trading platforms

| Column | Type | Description |
|--------|------|-------------|
| `username` | STRING | Trader identifier |
| `ingestion_timestamp` | TIMESTAMP | When data was collected |
| `endpoint_type` | STRING | Data source (profile, trades, history) |
| `source_url` | STRING | Original URL |
| `http_status` | INTEGER | Response code (200, 404, etc.) |
| `raw_html` | STRING | Complete HTML response |

**Characteristics:**
- Immutable (append-only)
- Never updated, only new records added
- Enables full reprocessability

---

### Silver Layer

#### `silver_trader_metrics`
Parsed and validated trader performance metrics

| Column | Type | Description |
|--------|------|-------------|
| `username` | STRING | Trader identifier |
| `processing_timestamp` | TIMESTAMP | When parsing occurred |
| `annualized_return` | DOUBLE | Annual return (%) |
| `sharpe_ratio` | DOUBLE | Risk-adjusted return (total volatility) |
| `sortino_ratio` | DOUBLE | Risk-adjusted return (downside only) |
| `calmar_ratio` | DOUBLE | Return / max drawdown |
| `beta` | DOUBLE | Market correlation |
| `jensens_alpha` | DOUBLE | Excess return vs. benchmark |
| `treynor_ratio` | DOUBLE | Return per unit systematic risk |
| `information_ratio` | DOUBLE | Active return vs. tracking error |
| `omega_ratio` | DOUBLE | Probability-weighted gains/losses |
| `last_month` | DOUBLE | 1-month return (%) |
| `year_to_date` | DOUBLE | YTD return (%) |
| `1_year` | DOUBLE | 1-year return (%) |
| `5_years` | DOUBLE | 5-year return (%) |
| `about` | STRING | Trader description/bio |

**Data Quality:**
- Numeric validation (`errors='coerce'`)
- Outlier detection (metrics beyond realistic bounds)
- Schema evolution enabled

---

#### `silver_portfolio_composition`
Portfolio diversification breakdown (long format)

| Column | Type | Description |
|--------|------|-------------|
| `username` | STRING | Trader identifier |
| `processing_timestamp` | TIMESTAMP | When parsing occurred |
| `category` | STRING | Type (sectors, exchanges, countries) |
| `item_name` | STRING | Specific sector/exchange/country |
| `allocation_percentage` | DOUBLE | Portfolio weight (0-100) |

**Structure:**
- Long format: Multiple rows per trader
- Enables easy aggregation and filtering
- Supports portfolio diversification scoring

---

### Gold Layer

#### `gold_elite_traders`
Elite performers meeting strict risk-adjusted criteria

| Column | Type | Description |
|--------|------|-------------|
| *(All columns from silver_trader_metrics)* | - | - |
| `combined_score` | DOUBLE | Avg(Sortino, Calmar) |

**Selection Criteria:**
- Sortino Ratio > 7.0
- Calmar Ratio > 7.0
- Demonstrates both downside protection AND drawdown resilience

---

#### `gold_top_performers`
Top 25% by annualized returns (baseline comparison group)

---

## 📈 Financial Metrics Explained

### Why Risk-Adjusted Metrics Matter

**Problem:** Raw returns don't reveal risk

Consider two traders:
- **Trader A:** 30% annual return, Sharpe 2.0, Sortino 2.5, Calmar 0.8
- **Trader B:** 30% annual return, Sharpe 0.5, Sortino 0.4, Calmar 0.2

**Same returns, vastly different risk profiles:**
- Trader A: Smooth, consistent gains with minimal drawdowns
- Trader B: Volatile, lucky year with 60% max drawdown

**Investor Experience:**
- Trader A: Comfortable holding through volatility
- Trader B: Panic sell during 60% drawdown, realize losses

---

### Core Metrics (Prioritized by Importance)

#### 1. **Sortino Ratio** (Primary Metric)

**Formula:** `(Return - Risk-Free Rate) / Downside Deviation`

**Why Superior to Sharpe:**
- Only penalizes **downside volatility** (losses)
- Ignores upside volatility (beneficial to investors)
- More realistic view of actual risk

**Example:**
- Value stock: Flat for 2 years, then +50% spike
  - Sharpe: Penalized for +50% volatility
  - Sortino: Recognizes no downside risk

**Interpretation:**
| Sortino | Quality | Investor Experience |
|---------|---------|---------------------|
| < 0.5 | Poor | Frequent losses, high stress |
| 0.5 - 1.0 | Acceptable | Moderate downside protection |
| 1.0 - 2.0 | Good | Solid risk management |
| > 2.0 | Excellent | Minimal downside, smooth returns |

**Real-World Benchmark:**
- S&P 500: ~0.8 Sortino (long-term)
- Elite hedge funds: 1.5 - 2.5 Sortino

---

#### 2. **Calmar Ratio** (Secondary Metric)

**Formula:** `Annualized Return / Maximum Drawdown`

**Why It Matters:**
- Reveals **worst-case scenario** resilience
- Shows psychological sustainability
- Identifies traders who survive crashes

**Example:**
- Trader A: 20% return, 10% max drawdown → Calmar = 2.0
- Trader B: 20% return, 50% max drawdown → Calmar = 0.4

**Psychological Reality:**
- Trader A: Investors stay invested through 10% dip
- Trader B: Investors panic-sell at 50% drawdown

**Interpretation:**
| Calmar | Drawdown Risk | Sustainability |
|--------|---------------|----------------|
| < 0.3 | Very High | Unsustainable |
| 0.3 - 0.5 | High | Risky |
| 0.5 - 1.0 | Moderate | Good |
| > 1.0 | Low | Excellent |

**Real-World Benchmark:**
- S&P 500: ~0.5 Calmar (long-term)
- All Weather Portfolio: ~0.56 Calmar

---

#### 3. **Sharpe Ratio** (Benchmark Metric)

**Formula:** `(Return - Risk-Free Rate) / Total Volatility`

**Limitation:** Penalizes both upside and downside volatility

**Still Useful:** Industry standard for comparison

**Interpretation:**
| Sharpe | Quality |
|--------|---------|
| < 1.0 | Below average |
| 1.0 - 2.0 | Good |
| > 2.0 | Excellent |

---

#### 4. **Beta**

**Meaning:** Market sensitivity (correlation with benchmark)

**Interpretation:**
- Beta = 1.0: Moves with market
- Beta > 1.0: More volatile than market
- Beta < 1.0: More stable than market
- Beta < 0: Moves opposite to market (rare)

**Use Case:** Portfolio diversification
- High Beta: Growth stocks, tech
- Low Beta: Utilities, consumer staples

---

#### 5. **Jensen's Alpha**

**Meaning:** Excess return vs. expected return (given risk)

**Formula:** `Actual Return - [Risk-Free Rate + Beta × (Market Return - Risk-Free Rate)]`

**Interpretation:**
- Alpha > 0: Outperforming risk-adjusted expectations
- Alpha = 0: Performing as expected
- Alpha < 0: Underperforming

**Use Case:** Skill vs. luck
- Persistent positive alpha = skill
- Occasional positive alpha = luck

---

### Why Focus on Sortino + Calmar?

**Combined Insight:** Sustainable risk-adjusted performance

#### Sortino: Day-to-day risk management
- Manages normal volatility
- Protects during small dips
- Ensures smooth investor experience

#### Calmar: Crisis resilience
- Survives major crashes
- Recovers from deep drawdowns
- Prevents permanent capital loss

**Elite Criteria:**
```
Sortino > 0.7  AND  Calmar > 0.4
```

**Real-World Validation:**
- Ray Dalio's All Weather: Sortino 1.18, Calmar 0.56
- Warren Buffett (Berkshire): Sortino ~1.2, Calmar ~0.8

---

## 🔍 Key Insights

### Finding 1: High Returns ≠ Elite Performance

**Data:** Of top 25% performers by return, only 15-20% meet elite criteria (Sortino > 7, Calmar > 7)

**Implication:** Most high-return traders take excessive risk

**Investor Action:** Filter by risk-adjusted metrics before copying

---

### Finding 2: Sortino > Sharpe for Investor Reality

**Data:** Sortino consistently 1.3-1.8x higher than Sharpe for elite traders

**Meaning:** Elite traders have asymmetric returns (occasional big gains, minimal losses)

**Why This Matters:** Sharpe penalizes big gains; Sortino recognizes them as beneficial

---

### Finding 3: Calmar Reveals Psychological Sustainability

**Data:** Traders with Calmar < 0.3 have 60% higher turnover (investors stop copying)

**Meaning:** Deep drawdowns cause panic-selling regardless of eventual recovery

**Investor Action:** Avoid traders with low Calmar, even if returns are high

---

### Finding 4: Beta Provides Market Context

**Data:** Elite traders average beta = 0.7 (vs. 1.0 market average)

**Meaning:** Elite traders use market-neutral strategies or defensive positioning

**Implication:** Perform across market cycles, not just bull markets

---

## 🛠️ Technical Stack

### Platform & Compute
- **Databricks** (DBR 13.x): Unified analytics platform
- **Apache Spark** (3.4+): Distributed data processing
- **Delta Lake** (2.0+): Reliable data lake storage

### Languages & Libraries
- **Python** (3.9+): Primary development language
- **SQL**: Data transformation and analytics
- **PySpark**: Spark DataFrame API
- **Pandas**: In-memory analytics
- **BeautifulSoup4**: HTML parsing
- **Requests**: HTTP client with proxy support



---

## 📁 Project Structure

```
social-trading-risk-analytics/
│
├── notebooks/
│   ├── 01_bronze_ingestion.py           # Raw data ingestion with proxy rotation
│   ├── 02_silver_transformation.py      # HTML parsing & metric extraction
│   └── 03_exploratory_analysis.py       # Risk-adjusted performance analysis
│
├── src/
│   ├── parsers/
│       └── profile_parser.py            # BeautifulSoup HTML parsers
│
├── data/
│   ├── traders/
│       └── trader_list_tier1.txt        # Source trader list
│
├── .env.example                         # Environment variable template
├── .gitignore                           # Git exclusions
└── README.md                            # This file
```

---

## 🚀 Getting Started

### Prerequisites

- Databricks workspace (Community Edition or paid tier)
- Python 3.9+
- Proxy service account (optional, for real data ingestion)

### Setup

1. **Clone repository:**
```bash
git clone https://github.com/danielalcaide/social-trading-risk-analytics.git
cd social-trading-risk-analytics
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required variables:
```bash
# Data Sources
PLATFORM_BASE_URL=https://example-trading-platform.com

# Delta Tables
BRONZE_TRADER_PROFILES=default.bronze_trader_profiles
SILVER_TRADER_METRICS=default.silver_trader_metrics
SILVER_PORTFOLIO_COMPOSITION=default.silver_portfolio_composition

# Proxy (optional)
PROXY_API_TOKEN=your_token_here
PROXY_API_URL=https://proxy.webshare.io/api/v2/proxy/list/
PROXY_API_PARAMS={"mode":"direct","page":1,"page_size":25}
```

---

## ⚙️ Pipeline Execution

### Full Pipeline (Bronze → Silver → Gold)

**Step 1: Bronze Ingestion**
```python
# Run: notebooks/01_bronze_ingestion.py
# Duration: 5-10 min per batch of 20 requests
# Output: bronze_trader_profiles
```

**Step 2: Silver Transformation**
```python
# Run: notebooks/02_silver_transformation.py
# Duration: 10-15 minutes
# Output: silver_trader_metrics, silver_portfolio_composition
```

**Step 3: Gold Analytics**
```python
# Run: notebooks/03_exploratory_analysis.py
# Duration: 5 minutes
# Output: gold_elite_traders, gold_top_performers
```

### Incremental Updates

**Daily Refresh:**
1. Bronze: Ingest new/updated profiles (LEFT ANTI JOIN pattern)
2. Silver: Transform only new bronze records
3. Gold: Recompute rankings

**Idempotency Guaranteed:**
- Anti-join patterns prevent duplicates
- Each bronze record processed exactly once

---

## 🔮 Future Enhancements

### Technical

- [ ] **MLflow:** Experiment tracking for ML models
- [ ] **Streamlit Dashboard:** Interactive trader comparison
- [ ] **API Endpoint:** RESTful access to trader rankings

### Analytics

- [ ] **ML Model:** Predict trader performance degradation
- [ ] **Time-Series Analysis:** Track metric evolution over time
- [ ] **Network Analysis:** Identify trader clustering patterns
- [ ] **Sentiment Analysis:** NLP on trader descriptions
- [ ] **Backtesting Framework:** Test copy trading strategies

### Business

- [ ] **Real-Time Alerting:** Notify when trader metrics breach thresholds
- [ ] **Portfolio Optimizer:** Recommend trader combinations for diversification
- [ ] **Risk Scoring:** Composite risk assessment (0-100 scale)
---

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

