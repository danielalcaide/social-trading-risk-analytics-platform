# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer Transformation: Trader Profile Parsing
# MAGIC
# MAGIC **Purpose:** Transform raw HTML (Bronze) into structured business entities (Silver)
# MAGIC
# MAGIC **Input:** `bronze_trader_profiles` - Raw HTML responses  
# MAGIC **Output:** 
# MAGIC - `silver_trader_metrics` - Risk-adjusted performance metrics
# MAGIC - `silver_portfolio_composition` - Portfolio diversification breakdown
# MAGIC
# MAGIC **Architecture Decision: Why Separate Bronze and Silver?**
# MAGIC
# MAGIC Bronze (Raw HTML) → Silver (Parsed Entities) pattern enables:
# MAGIC - **Reprocessability:** If parsing logic improves, reprocess from bronze
# MAGIC - **Debugging:** Inspect raw HTML when parsing fails
# MAGIC - **Evolution:** Platform HTML changes don't lose historical data
# MAGIC
# MAGIC **Key Technical Challenges:**
# MAGIC 1. **HTML Structure Variability:** Dynamic CSS classes, missing fields
# MAGIC 3. **Financial Metrics:** Parsing and validating risk ratios (Sharpe, Sortino, etc.)
# MAGIC 4. **Idempotency:** Process only new bronze records, avoid duplicates
# MAGIC
# MAGIC **Success Criteria:**
# MAGIC - 95%+ parsing success rate
# MAGIC - Valid financial metrics (bounded, numeric)
# MAGIC - Zero duplicate records in silver

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Environment Setup
# MAGIC
# MAGIC **Dependencies:**
# MAGIC - `beautifulsoup4`: HTML parsing library
# MAGIC - `autoreload`: Auto-reload custom modules during development
# MAGIC
# MAGIC **Why BeautifulSoup?**
# MAGIC - Robust HTML parsing with lenient error handling
# MAGIC - CSS selector support for targeting specific elements
# MAGIC - Handles malformed HTML gracefully

# COMMAND ----------

# MAGIC %pip install python-dotenv
# MAGIC %pip install beautifulsoup4
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %load_ext autoreload
# MAGIC %autoreload 2

# COMMAND ----------

import os
from dotenv import load_dotenv

env_path = os.path.join(
    os.path.dirname(os.getcwd()),
    '.env'
)
load_dotenv(env_path)

BRONZE_TRADER_PROFILES = os.getenv("BRONZE_TRADER_PROFILES")
SILVER_TRADER_METRICS = os.getenv("SILVER_TRADER_METRICS")
SILVER_PORTFOLIO_COMPOSITION = os.getenv("SILVER_PORTFOLIO_COMPOSITION")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Transformation Functions
# MAGIC
# MAGIC **Design Pattern: Separation of Concerns**
# MAGIC
# MAGIC Two distinct transformation functions:
# MAGIC
# MAGIC 1. `process_factsheet_data()` - Risk metrics and returns
# MAGIC 2. `process_portfolio_breakdowns()` - Diversification breakdown
# MAGIC
# MAGIC **Why Separate?**
# MAGIC
# MAGIC - Different schemas (wide vs. long format)
# MAGIC - Independent failure modes (metrics can succeed while portfolio fails)
# MAGIC - Clearer data lineage and debugging

# COMMAND ----------

import pandas as pd

def process_factsheet_data(factsheet_data, raw_html):
    """
    Process factsheet data and combine multiple DataFrames into a single optimized DataFrame.
    
    Args:
        factsheet_data (dict): Dictionary containing 'popular_investor_stats', 'returns', and 'about'
        raw_html (list): List containing dictionaries with 'timestamp' and 'user' keys
        
    Returns:
        pd.DataFrame: Combined and processed DataFrame
    """
    # Process investor stats (remove first key and convert to DataFrame)
    investor_stats = factsheet_data['popular_investor_stats'].copy()
    if investor_stats:  # Check if not empty
        investor_stats.pop(list(investor_stats.keys())[0])
    
    # Create and process returns DataFrame
    returns_df = pd.DataFrame([factsheet_data['returns']])
    if not returns_df.empty and len(returns_df.columns) > 0:
        returns_df = returns_df.rename(columns={returns_df.columns[0]: "LAST MONTH"})
        returns_df = returns_df.replace({'%': ''}, regex=True)
    
    # Create about DataFrame
    about_df = pd.DataFrame([factsheet_data['about']], columns=["about"])
    
    # Create investor stats DataFrame
    investor_df = pd.DataFrame([investor_stats])
    
    # Combine all DataFrames
    df_combined = pd.concat([returns_df, investor_df, about_df], axis=1)
    
    # Clean column names: replace spaces with underscores, remove quotes, lowercase
    df_combined.columns = (df_combined.columns
                          .str.replace(' ', '_')
                          .str.replace("'", '')
                          .str.lower())
    
    # Add metadata
    df_combined['timestamp'] = raw_html['timestamp']
    df_combined['user'] = raw_html['user']
    
    # Define numeric columns and convert
    numeric_columns = [
        'beta', 'sharpe_ratio', 'sortino_ratio', 'jensens_alpha', 
        'omega_ratio', 'treynor_ratio', 'information_ratio', 'calmar_ratio',
        'last_month', 'year_to_date', '1_year', '5_years', 'annualized_return'
    ]

    # Only convert columns that actually exist in the DataFrame
    existing_numeric_columns = [col for col in numeric_columns if col in df_combined.columns]

    df_combined[existing_numeric_columns] = df_combined[existing_numeric_columns].apply(
        pd.to_numeric, errors='coerce'
    )

    # Define the desired column order
    desired_order = ['user', 'timestamp'] + [col for col in df_combined.columns if col not in ['user', 'timestamp']]
    # Reorder the columns
    df_combined = df_combined[desired_order]

    
    return df_combined

def process_portfolio_breakdowns(breakdowns, raw_html):
    # Create a single DataFrame with all data
    rows = []
    for category, items in breakdowns.items():
        for item in items:
            rows.append({
                'category': category,
                'name': item['name'],
                'percentage': item['percentage']
            })

    df = pd.DataFrame(rows)

    def clean_percentage(pct_str):
        return float(pct_str.rstrip('%'))

    df['percentage'] = df['percentage'].apply(clean_percentage)

    # Add metadata
    df['timestamp'] = raw_html['timestamp']
    df['user'] = raw_html['user']
    
    return df

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Main Transformation Pipeline
# MAGIC
# MAGIC **Process Flow:**
# MAGIC ```
# MAGIC 1. Query bronze records needing transformation (LEFT ANTI JOIN)
# MAGIC 2. For each raw HTML record:
# MAGIC    a. Parse HTML with BeautifulSoup
# MAGIC    b. Extract structured data (custom parser module)
# MAGIC    c. Validate extraction (check for empty results)
# MAGIC    d. Transform to DataFrame (two separate functions)
# MAGIC    e. Accumulate results
# MAGIC 3. Write to silver tables (append mode, schema evolution enabled)
# MAGIC ```
# MAGIC
# MAGIC **Error Handling Strategy:**
# MAGIC - Log failed parses (empty stats) but continue processing
# MAGIC - Separate metrics and portfolio handling (independent failures)
# MAGIC - Accumulate all successes before writing (transactional)
# MAGIC
# MAGIC **Performance Consideration:**
# MAGIC - Accumulate in Pandas, batch write to Spark
# MAGIC - Avoids per-row Spark writes (expensive)

# COMMAND ----------

from bs4 import BeautifulSoup
from src.parser.profile_parser import extract_all_factsheet_data

raw_html = spark.sql(f"""
SELECT b.*
FROM {BRONZE_TRADER_PROFILES} b
LEFT ANTI JOIN {SILVER_TRADER_METRICS} f
ON b.user = f.user AND b.timestamp = f.timestamp
WHERE b.key = 'factsheet';
""").select('timestamp', 'user', 'response').collect()
    

factsheet_result = pd.DataFrame()
breakdowns_result = pd.DataFrame()

for row in raw_html:
    factsheet_html = row['response']
    soup_factsheet = BeautifulSoup(factsheet_html, 'html.parser')

    factsheet_data = extract_all_factsheet_data(soup_factsheet)

    # If not stats is returned an error may have occurred in the donwload_html process
    num_stats_returned = len(factsheet_data['popular_investor_stats'].values())
    if num_stats_returned == 0:
        print("Error: No stats returned for the user ", row['user'])
    else:
        print("User: ", row['user'])
        factsheet_df = process_factsheet_data(factsheet_data, row)
        factsheet_result = pd.concat([factsheet_result, factsheet_df], ignore_index=True)
            
        # If not values are returned the investor may have the portfolio emtpy
        total = sum(len(factsheet_data["portfolio_breakdowns"][key]) 
                for key in factsheet_data["portfolio_breakdowns"].keys())
        if total > 0:
            breakdowns_df = process_portfolio_breakdowns(
                factsheet_data['portfolio_breakdowns'],
                row
            )

        breakdowns_result = pd.concat([breakdowns_result, breakdowns_df], ignore_index=True)                    


# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Write to Silver Layer
# MAGIC
# MAGIC **Schema Evolution Enabled:**
# MAGIC - `mergeSchema=true` allows new columns to be added automatically
# MAGIC - Critical for financial data where platforms add new metrics
# MAGIC - Example: Platform adds "Max Drawdown" → automatically included
# MAGIC
# MAGIC **Write Mode: Append**
# MAGIC - Idempotency handled by upstream LEFT ANTI JOIN
# MAGIC - Each bronze record processed exactly once
# MAGIC - Silver layer grows incrementally with each run
# MAGIC
# MAGIC **Why Two Tables?**
# MAGIC - `silver_trader_metrics`: Wide format (1 row per trader)
# MAGIC - `silver_portfolio_composition`: Long format (multiple rows per trader)
# MAGIC - Different schemas → separate tables for query efficiency

# COMMAND ----------

# Convert Pandas DataFrames to Spark DataFrames
# Write to Silver Layer tables
# Mode "append": Add new records only (idempotency from query)
# mergeSchema: Allow new columns as platform evolves
breakdowns_result_spark = spark.createDataFrame(breakdowns_result)
breakdowns_result_spark.write.mode("append").option("mergeSchema", "true").saveAsTable(SILVER_PORTFOLIO_COMPOSITION)

factsheet_result_spark = spark.createDataFrame(factsheet_result)
factsheet_result_spark.write.mode("append").option("mergeSchema", "true").saveAsTable(SILVER_TRADER_METRICS)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Development/Debugging: Single Profile Test
# MAGIC
# MAGIC **Purpose:** Test parsing logic on a single profile for debugging
# MAGIC
# MAGIC **When to Use:**
# MAGIC - Developing new parsing rules
# MAGIC - Investigating parsing failures
# MAGIC - Validating schema changes
# MAGIC
# MAGIC **Process:**
# MAGIC 1. Fetch single profile from bronze
# MAGIC 2. Parse and extract data
# MAGIC 3. Display structured output
# MAGIC 4. Optionally save raw HTML for inspection

# COMMAND ----------

from bs4 import BeautifulSoup
from src.factsheet import extract_all_factsheet_data

raw_html = spark.table(BRONZE_TRADER_PROFILES).filter('key = "factsheet"').filter('user = "JamieMarc"').select('timestamp', 'user', 'response').head(1)

factsheet_html = raw_html[0]["response"]
with open("output.txt", "w") as file:
    file.write(factsheet_html)

soup_factsheet = BeautifulSoup(factsheet_html, "html.parser")

factsheet_data = extract_all_factsheet_data(soup_factsheet)

num_stats_returned = len(factsheet_data['popular_investor_stats'].values())

# If not stats is returned an error may have occurred in the donwload_html process
if num_stats_returned == 0:
    print("Error: No stats returned for the user ", row['user'])
else:
    print(factsheet_data)
    factsheet_df = process_factsheet_data(factsheet_data, raw_html[0],
    )
    total = sum(len(factsheet_data["portfolio_breakdowns"][key]) 
                for key in factsheet_data["portfolio_breakdowns"].keys())
    if total > 0:
        breakdowns_df = process_portfolio_breakdowns(
        factsheet_data["portfolio_breakdowns"], raw_html[0]
        )
