import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

DATA_DIR = "temp_audit_data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# SCENARIO 1: Small Clean
s1 = pd.DataFrame({
    "date": [datetime(2023, 1, i).strftime("%Y-%m-%d") for i in range(1, 11)],
    "revenue": [100, 150, 120, 200, 180, 250, 220, 300, 280, 350],
    "product": ["Widget A", "Widget B"] * 5
})
s1.to_csv(f"{DATA_DIR}/scenario_1_small_clean.csv", index=False, encoding='utf-8-sig')

# SCENARIO 2 & 7: Sampling from ecom_data.csv
try:
    ecom = pd.read_csv("ecom_data.csv", nrows=20000)
    # Scenario 2: Moderate sample (1,000 rows)
    ecom.head(1000).to_csv(f"{DATA_DIR}/scenario_2_ecommerce.csv", index=False, encoding='utf-8-sig')
    # Scenario 7: Large sample (15,000 rows)
    ecom.head(15000).to_csv(f"{DATA_DIR}/scenario_7_large.csv", index=False, encoding='utf-8-sig')
except Exception as e:
    print(f"Error sampling ecom_data.csv: {e}")

# SCENARIO 3: Messy Data (Currencies, mixed names, dates)
s3 = pd.DataFrame({
    "Date_String": ["Jan 1, 2023", "2023-01-02", "03-01-2023", "4/1/23", "2023.01.05"],
    "SaleAmount": ["$120.50", "\u00a3100", "\u20ac95", "110", "\u20b98000"],
    "prod_name": ["  iPhone 13", "iPhone 13  ", "iphone 13", "Samsung S22 ", " Samsung S22 "],
    "qty": [1, 2, 1, 3, 1]
})
s3.to_csv(f"{DATA_DIR}/scenario_3_messy.csv", index=False)

# SCENARIO 4: Quantity + UnitPrice fallback
s4 = pd.DataFrame({
    "date": ["2023-01-01"] * 5,
    "quantity": [10, 5, 2, 1, 20],
    "unit_price": [15.5, 20.0, 100.0, 50.0, 5.0],
    "product": ["A", "B", "C", "D", "E"]
})
s4.to_csv(f"{DATA_DIR}/scenario_4_quantity_unitprice.csv", index=False)

# SCENARIO 5: Missing Optional fields
s5 = pd.DataFrame({
    "revenue": [1000, 2000, 1500]
})
s5.to_csv(f"{DATA_DIR}/scenario_5_missing_optional.csv", index=False)

# SCENARIO 6: Baseline Pair
s6_cur = pd.DataFrame({
    "date": ["2023-02-01", "2023-02-02"],
    "revenue": [500, 600],
    "order_id": ["ORD1", "ORD2"]
})
s6_base = pd.DataFrame({
    "date": ["2023-01-01", "2023-01-02"],
    "revenue": [450, 550],
    "order_id": ["ORD_B1", "ORD_B2"]
})
s6_cur.to_csv(f"{DATA_DIR}/scenario_6_current.csv", index=False)
s6_base.to_csv(f"{DATA_DIR}/scenario_6_baseline.csv", index=False)

print("Test scenarios generated successfully in temp_audit_data/")
