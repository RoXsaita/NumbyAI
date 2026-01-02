#!/usr/bin/env python3
"""
Analyze bank statement CSV structure and output JSON analysis.
"""
import pandas as pd
import json
import re
from datetime import datetime
from io import StringIO

# Sample data provided by user
sample_data = """2025-11-29  02-01-2025                                                                                 '66 1090 1883 0000 0001 5438 0216                                       SUHEL E ABU AITTAH UL. SOKOŁOWSKA 11/124 01-142 WARSZAWA                               PLN  21483,27  26480,21  82  Unnamed: 8
30-01-2025  30-01-2025                                                                                      PWC wynagrodzenie za 01 2025  PRICEWATERHOUSECOOPERS POLSKA SP. Z O.O. SP.K. UL. POLNA 11 00-633 WARSZAWA ELIXIR 30-01-2025  27 1050 0086 1000 0090 3158 9790  10804,79  26480,21   1         NaN
31-01-2025  30-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 21.92 PLN GORACO POLECAM WARSZAWA                                                                                            NaN                               NaN    -21,92  26414,94   2         NaN
31-01-2025  30-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 43.35 PLN ZIKO APTEKA 23 WARSZAWA                                                                                            NaN                               NaN    -43,35  26436,86   3         NaN
30-01-2025  29-01-2025                                                 Prowizja za przewalutowanie transakcji dot.karty 557519******1802                                                                                            NaN                               NaN     -2,15  15675,42   4         NaN
30-01-2025  29-01-2025                   DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 18.00 USD 18.00 USD 1 USD=4.2655 PLN VENICE.AI SHERIDAN                                                                                            NaN                               NaN    -76,78  15677,57   5         NaN
29-01-2025  28-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 16.99 PLN ZABKA Z3074 K.1 WARSZAWA                                                                                            NaN                               NaN    -16,99  15754,35   6         NaN
28-01-2025  27-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 334.35 PLN LIDL KAPELANOW Warszawa                                                                                            NaN                               NaN   -334,35  15771,34   7         NaN
28-01-2025  27-01-2025                                 DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 99.97 PLN DECATHLON Warszawa Ost WARSZAWA                                                                                            NaN                               NaN    -99,97  16105,69   8         NaN
27-01-2025  26-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 162.00 PLN Krutoy Lounge Warszawa                                                                                            NaN                               NaN   -162,00  16205,66   9         NaN
26-01-2025  26-01-2025                                             Zakup BLIK PayU S.A.None Grunwaldzka 18660-166 Poznan ref:86082081517                                                     PayU S.A.None Grunwaldzka 18660-166 Poznan  72 1090 1489 0000 0000 4800 3393   -245,79  16367,66  10         NaN
26-01-2025  25-01-2025                                      DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 22.00 PLN WM SP zoo HORECA SP K Ilow                                                                                            NaN                               NaN    -22,00  16672,12  11         NaN
26-01-2025  25-01-2025                                           DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 10.00 PLN Klub Stodola Warszawa                                                                                            NaN                               NaN    -10,00  16694,12  12         NaN
26-01-2025  25-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 43.96 PLN ZABKA ZA757 K.1 WARSZAWA                                                                                            NaN                               NaN    -43,96  16613,45  13         NaN
26-01-2025  25-01-2025                                   DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 14.71 PLN WARZYWA I OWOCE ANIA Warszawa                                                                                            NaN                               NaN    -14,71  16657,41  14         NaN
26-01-2025  24-01-2025                                     DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 16.90 PLN VINCENT NOWY SWIAT WARSZAWA                                                                                            NaN                               NaN    -16,90  16704,12  15         NaN
24-01-2025  24-01-2025                                             Zakup BLIK PayU S.A.None Grunwaldzka 18660-166 Poznan ref:86040463936                                                     PayU S.A.None Grunwaldzka 18660-166 Poznan  72 1090 1489 0000 0000 4800 3393    -89,19  16762,91  16         NaN
24-01-2025  23-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 23.00 PLN ZABKA Z3074 K.1 WARSZAWA                                                                                            NaN                               NaN    -23,00  16739,91  17         NaN
24-01-2025  23-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 7.99 PLN ZABKA Z3074 K.1 WARSZAWA                                                                                            NaN                               NaN     -7,99  16852,10  18         NaN
24-01-2025  23-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 18.22 PLN ZABKA Z3074 K.1 WARSZAWA                                                                                            NaN                               NaN    -18,22  16860,09  19         NaN
24-01-2025  23-01-2025                                  DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 18.89 PLN CARREFOUR EXPRESS V55 WARSZAWA                                                                                            NaN                               NaN    -18,89  16721,02  20         NaN
24-01-2025  22-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 73.80 PLN MULTIKINO S.A. Warszawa                                                                                            NaN                               NaN    -73,80  16878,31  21         NaN
23-01-2025  22-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 27.47 PLN ZABKA Z3074 K.1 WARSZAWA                                                                                            NaN                               NaN    -27,47  16952,11  22         NaN
22-01-2025  21-01-2025                                   DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 11.66 PLN WARZYWA I OWOCE ANIA Warszawa                                                                                            NaN                               NaN    -11,66  16979,58  23         NaN
21-01-2025  20-01-2025                                   DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 8.79 PLN CARREFOUR EXPRESS V55 WARSZAWA                                                                                            NaN                               NaN     -8,79  16991,24  24         NaN
21-01-2025  20-01-2025                                   DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 5.29 PLN CARREFOUR EXPRESS V55 WARSZAWA                                                                                            NaN                               NaN     -5,29  17000,03  25         NaN
20-01-2025  20-01-2025                                                 Prowizja za przewalutowanie transakcji dot.karty 557519******1802                                                                                            NaN                               NaN     -1,86  17005,32  26         NaN
20-01-2025  19-01-2025  DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 15.58 USD 15.58 USD 1 USD=4.2655 PLN X CORP. PAID FEATURES SAN FRANCISCO                                                                                            NaN                               NaN    -66,46  17007,18  27         NaN
19-01-2025  18-01-2025                                  DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 8.98 PLN PL KFC WARSZAWA PROMEN Warszawa                                                                                            NaN                               NaN     -8,98  17118,62  28         NaN
19-01-2025  18-01-2025                                           DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 193.21 PLN KAUFLAND 05 WARSZAWA                                                                                            NaN                               NaN   -193,21  17127,60  29         NaN
19-01-2025  18-01-2025                                           DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 44.98 PLN ROSSMANN 169 WARSZAWA                                                                                            NaN                               NaN    -44,98  17073,64  30         NaN
19-01-2025  17-01-2025                                  DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 1.89 PLN JMP S.A. BIEDRONKA 538 WARSZAWA                                                                                            NaN                               NaN     -1,89  17339,30  31         NaN
19-01-2025  17-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 18.49 PLN ZABKA ZB602 K.2 WARSZAWA                                                                                            NaN                               NaN    -18,49  17320,81  32         NaN
19-01-2025  17-01-2025                                          DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 2.98 PLN GORACO POLECAM WARSZAWA                                                                                            NaN                               NaN     -2,98  17341,19  33         NaN
17-01-2025  17-01-2025                                                 Prowizja za przewalutowanie transakcji dot.karty 557519******1802                                                                                            NaN                               NaN     -1,18  17479,64  34         NaN
17-01-2025  16-01-2025    DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 9.84 USD 9.84 USD 1 USD=4.2655 PLN X CORP. PAID FEATURES SAN FRANCISCO                                                                                            NaN                               NaN    -41,97  17480,82  35         NaN
17-01-2025  16-01-2025                                  DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 93.01 PLN CARREFOUR HIPERMARKET WARSZAWA                                                                                            NaN                               NaN    -93,01  17437,18  36         NaN
17-01-2025  16-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 12.99 PLN UBER *ONE HELP.UBER.COM                                                                                            NaN                               NaN    -12,99  17450,17  37         NaN
17-01-2025  16-01-2025                                         DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 29.47 PLN GORACO POLECAM WARSZAWA                                                                                            NaN                               NaN    -29,47  17522,79  38         NaN
15-01-2025  14-01-2025                                DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 388.31 PLN LIDL BORA KOMOROWSKIEG WARSZAWA                                                                                            NaN                               NaN   -388,31  17522,79  39         NaN
14-01-2025  13-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 17.98 PLN ZABKA ZA757 K.1 WARSZAWA                                                                                            NaN                               NaN    -17,98  17911,10  40         NaN
13-01-2025  12-01-2025                                     DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 53.15 PLN APTEKA OD SERCA 02 WARSZAWA                                                                                            NaN                               NaN    -53,15  17929,08  41         NaN
12-01-2025  11-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 24.56 PLN UBER *TRIP HELP.UBER.COM                                                                                            NaN                               NaN    -24,56  17982,23  42         NaN
11-01-2025  10-01-2025                                  DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 67.80 PLN CINEMA CITY PROMENADA WARSZAWA                                                                                            NaN                               NaN    -67,80  18086,71  43         NaN
11-01-2025  10-01-2025                                               DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 79.92 PLN THAI WOK WARSZAWA                                                                                            NaN                               NaN    -79,92  18006,79  44         NaN
11-01-2025  10-01-2025                                  DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 43.62 PLN CARREFOUR HIPERMARKET WARSZAWA                                                                                            NaN                               NaN    -43,62  18154,51  45         NaN
10-01-2025  10-01-2025                                                 Prowizja za przewalutowanie transakcji dot.karty 557519******1802                                                                                            NaN                               NaN     -0,51  18352,34  46         NaN
10-01-2025  09-01-2025                               DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 107.93 PLN DNH*GODADDY.COM PLN 480-505-8855                                                                                            NaN                               NaN   -107,93  18244,41  47         NaN
10-01-2025  09-01-2025                                   DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 46.28 PLN WARZYWA I OWOCE ANIA Warszawa                                                                                            NaN                               NaN    -46,28  18198,13  48         NaN
09-01-2025  08-01-2025                                 DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 21.07 PLN JMP S.A. BIEDRONKA 483 WARSZAWA                                                                                            NaN                               NaN    -21,07  18404,89  49         NaN
10-01-2025  08-01-2025                                  DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 33.80 PLN GREEN COFFEE SP Z O O WARSZAWA                                                                                            NaN                               NaN    -33,80  18371,09  50         NaN"""

# Try reading the CSV - it appears to be space-separated with multiple spaces
# First row seems to be account info, not a header
try:
    # Try reading with multiple spaces as separator
    df = pd.read_csv(StringIO(sample_data), header=None, sep=r'\s{2,}', engine='python', skipinitialspace=True)
except Exception as e:
    # Fallback: read with default separator
    df = pd.read_csv(StringIO(sample_data), header=None, skipinitialspace=True)

# Remove the first row (account summary) for analysis
df_data = df.iloc[1:].copy()

print(f"DataFrame shape: {df_data.shape}")
print(f"Number of columns: {len(df_data.columns)}")
print(f"\nColumn analysis:")
for i in range(min(10, len(df_data.columns))):
    sample_values = df_data.iloc[:5, i].dropna().tolist()
    print(f"Column {i}: {sample_values[:3]}")

# Analyze columns
columns_found = [f"Column {i}" for i in range(len(df_data.columns))]

# Identify date columns
date_column = None
date_format = None
date_patterns = [
    (r'^\d{2}-\d{2}-\d{4}$', 'DD-MM-YYYY'),
    (r'^\d{4}-\d{2}-\d{2}$', 'YYYY-MM-DD'),
    (r'^\d{2}/\d{2}/\d{4}$', 'DD/MM/YYYY'),
    (r'^\d{2}/\d{2}/\d{4}$', 'MM/DD/YYYY'),
]

for i in range(min(3, len(df_data.columns))):
    col_data = df_data.iloc[:, i].dropna().astype(str)
    if len(col_data) > 0:
        # Check if column contains dates
        matches = 0
        matched_format = None
        for pattern, fmt in date_patterns:
            col_matches = sum(1 for val in col_data.head(20) if re.match(pattern, str(val).strip()))
            if col_matches > matches:
                matches = col_matches
                matched_format = fmt
        if matches >= 15:  # At least 15 out of 20 match
            date_column = f"Column {i}"
            date_format = matched_format
            break

# Identify description column (long text, contains transaction descriptions)
description_column = None
for i in range(len(df_data.columns)):
    col_data = df_data.iloc[:, i].dropna().astype(str)
    if len(col_data) > 0:
        avg_length = col_data.str.len().mean()
        sample = str(col_data.iloc[0]).upper()
        # Check for transaction keywords
        has_keywords = any(kw in sample for kw in ['PŁATNOŚĆ', 'DOP', 'ZAKUP', 'PROWIZJA', 'WYNAGRODZENIE', 'BLIK'])
        if avg_length > 30 and has_keywords:
            description_column = f"Column {i}"
            break

# Identify amount column (numeric with comma decimal separator)
amount_column = None
for i in range(len(df_data.columns)):
    col_data = df_data.iloc[:, i].dropna().astype(str)
    if len(col_data) > 0:
        # Look for pattern like -21,92 or 10804,79
        matches = sum(1 for val in col_data.head(20) if re.search(r'^-?\d+[.,]\d{2}$', str(val).strip()))
        if matches >= 15:
            amount_column = f"Column {i}"
            break

# Identify balance column (positive numbers, typically after amount)
balance_column = None
if amount_column:
    amount_idx = int(amount_column.split()[-1])
    for i in range(amount_idx + 1, min(amount_idx + 3, len(df_data.columns))):
        col_data = df_data.iloc[:, i].dropna().astype(str)
        if len(col_data) > 0:
            # Balance should be positive numbers with comma decimal
            matches = sum(1 for val in col_data.head(20) 
                         if re.search(r'^\d+[.,]\d{2}$', str(val).strip()) and not str(val).strip().startswith('-'))
            if matches >= 15:
                balance_column = f"Column {i}"
                break

# Determine currency
currency = "PLN"
if "PLN" in sample_data.upper():
    currency = "PLN"

# Determine if positive amounts are debit or credit
# Looking at the data: positive amounts like 10804,79 appear to be income (credit)
# Negative amounts like -21,92 appear to be expenses (debit)
amount_positive_is = "credit"

# Check if first row is header
has_headers = False
skip_rows = 1  # Skip the first row which appears to be account summary

# Questions for user
questions = []

if not date_column:
    questions.append("Could not definitively identify the date column. Please specify which column contains transaction dates.")
elif date_column == "Column 0":
    # Check if there's a second date column
    col1_data = df_data.iloc[:, 1].dropna().astype(str)
    if len(col1_data) > 0:
        col1_matches = sum(1 for val in col1_data.head(20) if re.match(r'^\d{2}-\d{2}-\d{4}$', str(val).strip()))
        if col1_matches >= 15:
            questions.append("Found two date columns (Column 0 and Column 1). Column 0 appears to be posting date, Column 1 appears to be value date. Should we use Column 0 for transaction dates?")

if not description_column:
    questions.append("Could not definitively identify the description column. Please specify which column contains transaction descriptions.")

if not amount_column:
    questions.append("Could not definitively identify the amount column. Please specify which column contains transaction amounts.")

if not balance_column:
    questions.append("Could not definitively identify the balance column. Please specify which column contains account balance after each transaction.")

# Confidence level
confidence = "high" if (date_column and description_column and amount_column and balance_column) else "medium"
if len(questions) > 2:
    confidence = "low"

# Build result
result = {
    "columns_found": columns_found,
    "date_column": date_column or "Unknown",
    "description_column": description_column or "Unknown",
    "amount_column": amount_column or "Unknown",
    "balance_column": balance_column or "Unknown",
    "date_format": date_format or "Unknown",
    "currency": currency,
    "has_headers": has_headers,
    "skip_rows": skip_rows,
    "amount_positive_is": amount_positive_is,
    "questions": questions,
    "confidence": confidence
}

# Output JSON
print("\n" + "="*60)
print("ANALYSIS RESULT (JSON):")
print("="*60)
print(json.dumps(result, indent=2, ensure_ascii=False))
