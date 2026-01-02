#!/usr/bin/env python3
"""
Temporary script to analyze CSV structure from the provided sample.
"""
import pandas as pd
import json
import re
from datetime import datetime

# Sample data provided by user
sample_data = """2025-11-29  02-01-2025                                                                                 '66 1090 1883 0000 0001 5438 0216                                       SUHEL E ABU AITTAH UL. SOKOŁOWSKA 11/124 01-142 WARSZAWA                               PLN  21483,27  26480,21  82  Unnamed: 8
30-01-2025  30-01-2025                                                                                      PWC wynagrodzenie za 01 2025  PRICEWATERHOUSECOOPERS POLSKA SP. Z O.O. SP.K. UL. POLNA 11 00-633 WARSZAWA ELIXIR 30-01-2025  27 1050 0086 1000 0090 3158 9790  10804,79  26480,21   1         NaN
31-01-2025  30-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 21.92 PLN GORACO POLECAM WARSZAWA                                                                                            NaN                               NaN    -21,92  26414,94   2         NaN
31-01-2025  30-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 43.35 PLN ZIKO APTEKA 23 WARSZAWA                                                                                            NaN                               NaN    -43,35  26436,86   3         NaN
30-01-2025  29-01-2025                                                 Prowizja za przewalutowanie transakcji dot.karty 557519******1802                                                                                            NaN                               NaN     -2,15  15675,42   4         NaN"""

# Write to temp file
with open('/tmp/sample_statement.csv', 'w', encoding='utf-8') as f:
    f.write(sample_data)

# Try reading with different configurations
print("=== Analysis 1: Reading with headers ===")
try:
    df1 = pd.read_csv('/tmp/sample_statement.csv', header=0, encoding='utf-8')
    print(f"Shape: {df1.shape}")
    print(f"Columns: {list(df1.columns)}")
    print(f"\nFirst row:\n{df1.iloc[0]}")
    print(f"\nSecond row:\n{df1.iloc[1]}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Analysis 2: Reading without headers, skip first row ===")
try:
    df2 = pd.read_csv('/tmp/sample_statement.csv', header=None, skiprows=1, encoding='utf-8')
    print(f"Shape: {df2.shape}")
    print(f"Columns (as indices): {list(range(len(df2.columns)))}")
    print(f"\nFirst data row:\n{df2.iloc[0]}")
    print(f"\nColumn 0 (first few values): {df2.iloc[:3, 0].tolist()}")
    print(f"\nColumn 1 (first few values): {df2.iloc[:3, 1].tolist()}")
    print(f"\nColumn 2 (first few values): {df2.iloc[:3, 2].tolist()}")
    print(f"\nColumn 5 (first few values): {df2.iloc[:3, 5].tolist()}")
    print(f"\nColumn 6 (first few values): {df2.iloc[:3, 6].tolist()}")
except Exception as e:
    print(f"Error: {e}")

# Analyze date format
print("\n=== Date Format Analysis ===")
date_samples = ["30-01-2025", "31-01-2025", "29-01-2025"]
for date_str in date_samples:
    try:
        parsed = datetime.strptime(date_str, '%d-%m-%Y')
        print(f"{date_str} -> {parsed.date()} (DD-MM-YYYY format)")
    except:
        pass

# Analyze currency
print("\n=== Currency Analysis ===")
currency_indicators = ["PLN", "polski", "złoty", "zloty"]
found_currency = None
for indicator in currency_indicators:
    if indicator in sample_data.upper():
        found_currency = "PLN"
        print(f"Found currency indicator: {indicator} -> Currency: PLN")
        break

# Analyze amount format
print("\n=== Amount Format Analysis ===")
amount_samples = ["10804,79", "-21,92", "-43,35", "-2,15"]
print("Amounts use comma as decimal separator")
print("Positive amounts appear to be credits (income)")
print("Negative amounts appear to be debits (expenses)")
