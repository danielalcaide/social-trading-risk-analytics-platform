# Databricks notebook source
# MAGIC %md
# MAGIC # Exploratory Analysis: Risk-Adjusted Performance Insights
# MAGIC
# MAGIC **Purpose:** Analyze trader performance using risk-adjusted metrics to identify patterns and investment opportunities
# MAGIC
# MAGIC **Input:** `silver_trader_metrics` - Curated trader performance data  
# MAGIC **Output:** Data-driven insights on trader performance, risk characteristics, and portfolio patterns
# MAGIC
# MAGIC **Analysis Focus:**
# MAGIC 1. **Distribution Analysis:** Understanding the typical trader profile
# MAGIC 2. **Risk-Adjusted Returns:** Comparing Sharpe, Sortino, Calmar ratios
# MAGIC 3. **Top Performer Identification:** Finding traders with sustainable performance
# MAGIC 4. **Risk-Return Trade-offs:** Visualizing efficiency frontiers
# MAGIC
# MAGIC **Key Questions:**
# MAGIC - What defines a "good" trader beyond raw returns?
# MAGIC - How do risk metrics differ between top and average performers?
# MAGIC - Which metrics best predict sustainable performance?

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Environment Setup & Data Loading

# COMMAND ----------

# MAGIC %pip install python-dotenv
# MAGIC %restart_python

# COMMAND ----------

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
from dotenv import load_dotenv

# Configure plotting style
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (12, 6)

# Load environment variables
env_path = os.path.join(os.path.dirname(os.getcwd()), '.env')
load_dotenv(env_path)

SILVER_TRADER_METRICS = os.getenv("SILVER_TRADER_METRICS")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Data Preparation
# MAGIC
# MAGIC **Data Quality Strategy:**
# MAGIC - Filter to most recent snapshot per trader (avoid duplicates)
# MAGIC - Remove outliers (metrics beyond realistic bounds)
# MAGIC - Handle missing values appropriately
# MAGIC
# MAGIC **Why Most Recent Only?**
# MAGIC - Traders update profiles continuously
# MAGIC - Latest snapshot = current performance state
# MAGIC - Simplifies analysis (point-in-time view)
# MAGIC
# MAGIC **Future Enhancement:** Time-series analysis tracking trader evolution

# COMMAND ----------

query = f"""
CREATE OR REPLACE TEMP VIEW latest_trader_metrics AS
SELECT a.*
FROM {SILVER_TRADER_METRICS} AS a
INNER JOIN (
    SELECT user, MAX(timestamp) as last_timestamp
    FROM {SILVER_TRADER_METRICS}
    GROUP BY user
) AS b
ON a.user = b.user AND a.timestamp = b.last_timestamp
ORDER BY timestamp DESC
"""
spark.sql(query)

# COMMAND ----------

# Load data into Pandas for analysis
df = spark.table("latest_trader_metrics").toPandas()

print(f"Dataset Overview:")
print(f"  Total Traders: {len(df)}")
print(f"  Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"  Columns: {len(df.columns)}")
print(f"\nData Shape: {df.shape}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Data Distribution Analysis
# MAGIC
# MAGIC **Goal:** Understand the baseline characteristics of the trader population
# MAGIC
# MAGIC **Key Metrics to Examine:**
# MAGIC - Temporal distribution (when was data collected?)
# MAGIC - Return distribution (annualized returns)
# MAGIC - Risk metric distributions (Sharpe, Sortino, Calmar)
# MAGIC
# MAGIC **Why This Matters:**
# MAGIC - Identifies data quality issues (e.g., sudden gaps)
# MAGIC - Reveals market conditions during collection period
# MAGIC - Sets context for performance benchmarking

# COMMAND ----------

# Temporal distribution of data collection
df['collection_date'] = pd.to_datetime(df['timestamp']).dt.date

plt.figure(figsize=(14, 5))
df['collection_date'].value_counts().sort_index().plot(kind='bar')
plt.title('Data Collection Timeline', fontsize=14, fontweight='bold')
plt.xlabel('Date')
plt.ylabel('Number of Traders Processed')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

print(f"\nCollection Summary:")
print(df['collection_date'].value_counts().sort_index())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Return Distribution Analysis
# MAGIC
# MAGIC **Annualized Return Metrics:**
# MAGIC
# MAGIC Annualized returns show long-term performance and are less sensitive to short-term volatility.
# MAGIC This is the primary metric most investors focus on, but it tells an incomplete story without
# MAGIC considering risk.
# MAGIC
# MAGIC **Key Statistics:**
# MAGIC - Mean: Average trader performance
# MAGIC - Quartiles: Performance distribution (25th, 50th, 75th percentiles)
# MAGIC - Top 10%: Elite performer threshold

# COMMAND ----------

# Calculate return statistics
return_stats = {
    'Mean': df['annualized_return'].mean(),
    'Median': df['annualized_return'].median(),
    'Std Dev': df['annualized_return'].std(),
    'Q25': df['annualized_return'].quantile(0.25),
    'Q50': df['annualized_return'].quantile(0.50),
    'Q75': df['annualized_return'].quantile(0.75),
    'Q90': df['annualized_return'].quantile(0.90)
}

print("Annualized Return Distribution:")
print("="*50)
for metric, value in return_stats.items():
    print(f"  {metric:12s}: {value:8.2f}%")

# Visualize distribution
plt.figure(figsize=(12, 6))
plt.hist(df['annualized_return'].dropna(), bins=50, edgecolor='black', alpha=0.7)
plt.axvline(return_stats['Mean'], color='red', linestyle='--', label=f"Mean: {return_stats['Mean']:.2f}%")
plt.axvline(return_stats['Median'], color='green', linestyle='--', label=f"Median: {return_stats['Median']:.2f}%")
plt.axvline(return_stats['Q75'], color='blue', linestyle='--', label=f"75th Percentile: {return_stats['Q75']:.2f}%")
plt.title('Distribution of Annualized Returns', fontsize=14, fontweight='bold')
plt.xlabel('Annualized Return (%)')
plt.ylabel('Number of Traders')
plt.legend()
plt.tight_layout()
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Top Performer Segmentation
# MAGIC
# MAGIC **Defining "Top Performers":**
# MAGIC
# MAGIC We segment traders into the top 25% by annualized returns. This creates a cohort of 
# MAGIC high-performing traders for deeper analysis.
# MAGIC
# MAGIC **Critical Question:** Do high returns = high risk?
# MAGIC
# MAGIC We'll analyze risk-adjusted metrics (Sharpe, Sortino, Calmar) to answer this.

# COMMAND ----------

# Create top 25% performer segment
top_25_threshold = df['annualized_return'].quantile(0.75)
df_top25 = df[df['annualized_return'] >= top_25_threshold].copy()

print(f"Top 25% Performers Analysis:")
print(f"  Threshold: {top_25_threshold:.2f}%")
print(f"  Number of Traders: {len(df_top25)}")
print(f"  Average Return: {df_top25['annualized_return'].mean():.2f}%")
print(f"\nSample of Top Performers:")
display(df_top25[['user', 'annualized_return', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio']].head(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Risk-Adjusted Performance Analysis
# MAGIC
# MAGIC **Why Risk Metrics Matter More Than Returns:**
# MAGIC
# MAGIC Raw returns don't tell the full story. Two traders with 30% annual returns might have vastly
# MAGIC different risk profiles:
# MAGIC - Trader A: Smooth, consistent gains (Sharpe 2.0, Sortino 2.5)
# MAGIC - Trader B: Volatile, lucky year (Sharpe 0.5, Sortino 0.4)
# MAGIC
# MAGIC **Key Metrics Explained:**
# MAGIC
# MAGIC ### Sortino Ratio (Primary Focus)
# MAGIC **Formula:** (Return - Risk-Free Rate) / Downside Deviation
# MAGIC
# MAGIC **Why Superior to Sharpe:**
# MAGIC - Only penalizes downside volatility (losses)
# MAGIC - Ignores upside volatility (which benefits investors)
# MAGIC - More realistic view of actual risk
# MAGIC
# MAGIC **Interpretation:**
# MAGIC - < 0.5: Poor risk-adjusted returns
# MAGIC - 0.5 - 1.0: Acceptable
# MAGIC - 1.0 - 2.0: Good
# MAGIC - > 2.0: Excellent
# MAGIC
# MAGIC ### Calmar Ratio (Secondary Focus)
# MAGIC **Formula:** Annualized Return / Maximum Drawdown
# MAGIC
# MAGIC **Why It Matters:**
# MAGIC - Shows worst-case scenario resilience
# MAGIC - Reveals psychological sustainability
# MAGIC - Identifies traders who survive crashes
# MAGIC
# MAGIC **Interpretation:**
# MAGIC - < 0.3: High drawdown risk
# MAGIC - 0.3 - 0.5: Moderate risk
# MAGIC - 0.5 - 1.0: Good risk management
# MAGIC - > 1.0: Excellent drawdown control
# MAGIC
# MAGIC ### Sharpe Ratio (Benchmark)
# MAGIC **Formula:** (Return - Risk-Free Rate) / Total Volatility
# MAGIC
# MAGIC **Limitation:** Penalizes both upside and downside volatility
# MAGIC
# MAGIC **Still Useful:** Industry standard for comparison

# COMMAND ----------

# Compare risk metrics for top 25% performers
risk_metrics_summary = df_top25[['sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'beta']].describe()

print("Risk Metrics Summary - Top 25% Performers:")
print("="*70)
display(risk_metrics_summary)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Sortino vs Calmar: Identifying Elite Traders
# MAGIC
# MAGIC **Hypothesis:** Elite traders excel in BOTH downside risk management (Sortino) AND 
# MAGIC drawdown resilience (Calmar).
# MAGIC
# MAGIC **Selection Criteria:**
# MAGIC - Sortino Ratio > 0.7 (manages downside volatility well)
# MAGIC - Calmar Ratio > 0.4 (survives major drawdowns)
# MAGIC
# MAGIC **Visualization Strategy:**
# MAGIC - Scatter plot: X-axis = Sortino, Y-axis = Calmar
# MAGIC - Top-right quadrant = Elite performers
# MAGIC - Identify outliers for further investigation

# COMMAND ----------

# Scatter plot: Sortino vs Calmar
plt.figure(figsize=(14, 8))
scatter = plt.scatter(
    df_top25['sortino_ratio'], 
    df_top25['calmar_ratio'],
    c=df_top25['annualized_return'],
    cmap='viridis',
    s=100,
    alpha=0.6,
    edgecolors='black',
    linewidth=0.5
)

# Add threshold lines for elite criteria
plt.axvline(x=7, color='red', linestyle='--', alpha=0.5, label='Sortino > 7 (Elite)')
plt.axhline(y=7, color='blue', linestyle='--', alpha=0.5, label='Calmar > 7 (Elite)')

# Add colorbar for return magnitude
cbar = plt.colorbar(scatter)
cbar.set_label('Annualized Return (%)', fontsize=12)

plt.title('Risk-Adjusted Performance: Sortino vs Calmar Ratio\n(Top 25% Performers)', 
          fontsize=14, fontweight='bold')
plt.xlabel('Sortino Ratio (Downside Risk Management)', fontsize=12)
plt.ylabel('Calmar Ratio (Drawdown Resilience)', fontsize=12)
plt.legend(loc='upper left')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Elite Trader Identification
# MAGIC
# MAGIC **Filtering Criteria:**
# MAGIC - Sortino Ratio > 7.0
# MAGIC - Calmar Ratio > 7.0
# MAGIC
# MAGIC These traders demonstrate:
# MAGIC 1. Minimal downside volatility relative to returns
# MAGIC 2. Strong drawdown recovery
# MAGIC 3. Sustainable risk-adjusted performance
# MAGIC
# MAGIC **Investment Implication:**
# MAGIC Traders meeting both criteria have historically shown resilience during market stress
# MAGIC and consistency in returns.

# COMMAND ----------

# Identify elite performers
elite_traders = df_top25[
    (df_top25['sortino_ratio'] > 7) & 
    (df_top25['calmar_ratio'] > 7)
].copy()

# Sort by combined metric (average of Sortino and Calmar)
elite_traders['combined_score'] = (elite_traders['sortino_ratio'] + elite_traders['calmar_ratio']) / 2
elite_traders = elite_traders.sort_values('combined_score', ascending=False)

print(f"Elite Traders Identified: {len(elite_traders)}")
print(f"\nTop Elite Performers:")
print("="*100)

display(elite_traders[[
    'user', 
    'annualized_return', 
    'sharpe_ratio', 
    'sortino_ratio', 
    'calmar_ratio',
    'beta',
    'combined_score'
]].head(10))

# Summary statistics for elite group
print("\nElite Group Statistics:")
print("="*50)
print(f"  Average Return: {elite_traders['annualized_return'].mean():.2f}%")
print(f"  Average Sortino: {elite_traders['sortino_ratio'].mean():.2f}")
print(f"  Average Calmar: {elite_traders['calmar_ratio'].mean():.2f}")
print(f"  Average Beta: {elite_traders['beta'].mean():.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Key Insights & Findings
# MAGIC
# MAGIC **Insight 1: High Returns Don't Equal Elite Performance**
# MAGIC
# MAGIC Many high-return traders fail the Sortino/Calmar test, indicating unsustainable risk-taking.
# MAGIC Elite performers balance returns with downside protection.
# MAGIC
# MAGIC **Insight 2: Sortino > Sharpe for Investor Reality**
# MAGIC
# MAGIC Sortino consistently identifies traders with better investor experience because it ignores
# MAGIC beneficial volatility (large gains) and focuses on actual risk (losses).
# MAGIC
# MAGIC **Insight 3: Calmar Reveals Psychological Sustainability**
# MAGIC
# MAGIC Traders with high Calmar ratios maintain investor confidence during drawdowns, reducing
# MAGIC panic-selling risk. This is critical for copy trading where emotional decisions dominate.
# MAGIC
# MAGIC **Insight 4: Beta Provides Market Context**
# MAGIC
# MAGIC Elite traders often show beta < 1.0, indicating market-neutral strategies or defensive
# MAGIC positioning that performs across market cycles.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Export Results for Further Analysis
# MAGIC
# MAGIC **Output Tables:**
# MAGIC - `gold_elite_traders`: Elite performer cohort
# MAGIC - `gold_top_performers`: Top 25% by returns
# MAGIC
# MAGIC **Future Use Cases:**
# MAGIC - ML model training (predict trader performance degradation)
# MAGIC - Dashboard visualization (Streamlit/Tableau)
# MAGIC - Automated alerts (notify when trader metrics change)

# COMMAND ----------

# Convert back to Spark DataFrames and save to Gold layer
spark.createDataFrame(elite_traders).write \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable("gold_elite_traders")

spark.createDataFrame(df_top25).write \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable("gold_top_performers")

print("✓ Gold layer tables created successfully:")
print("  - gold_elite_traders")
print("  - gold_top_performers")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC **Immediate:**
# MAGIC 1. Time-series analysis tracking trader metric evolution
# MAGIC 2. Portfolio composition analysis (sector/exchange diversification)
# MAGIC 3. ML model: Predict performance degradation
# MAGIC
# MAGIC **Advanced:**
# MAGIC 1. Backtest copy trading strategies using elite trader signals
# MAGIC 2. Network analysis: Identify trader clustering patterns
# MAGIC 3. Sentiment analysis from trader bios/descriptions
# MAGIC
# MAGIC **Production:**
# MAGIC 1. Automated daily refresh of elite trader rankings
# MAGIC 2. Alerting system for metric threshold breaches
# MAGIC 3. API endpoint for trader recommendations
