#!/usr/bin/env python3
"""
Analyze Santander bank statement CSV structure.
"""
import pandas as pd
import json
import re
from datetime import datetime

# Sample data from user
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
23-01-2025  22-01-2025                                        DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 27.47 PLN ZABKA Z6502 K.1 WARSZAWA                                                                                            NaN                               NaN    -27,47  16952,11  22         NaN
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
19-01-2025  17-01-2025                                          DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 2.98 PLN GORACO POLECAM WARSZAWA                                                                 NaN                               NaN     -2,98  17341,19  33         NaN
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

# Write to temp file
with open('/tmp/santander_sample.csv', 'w', encoding='utf-8') as f:
    f.write(sample_data)

# Read CSV - first row appears to be metadata/header, skip it
print("Reading CSV without headers, skipping first row...")
df = pd.read_csv('/tmp/santander_sample.csv', header=None, skiprows=1, encoding='utf-8', sep='\t', engine='python')

print(f"\nDataFrame shape: {df.shape}")
print(f"Number of columns: {len(df.columns)}")

# Analyze each column
print("\n=== Column Analysis ===")
column_analysis = []
for i in range(len(df.columns)):
    col = df.iloc[:, i]
    non_null = col.dropna()
    sample_values = non_null.head(5).tolist() if len(non_null) > 0 else []
    
    # Detect column type
    col_type = "unknown"
    if i == 0:
        # Check if it's a date
        if len(non_null) > 0:
            first_val = str(non_null.iloc[0])
            if re.match(r'\d{2}-\d{2}-\d{4}', first_val):
                col_type = "date (transaction date)"
    elif i == 1:
        if len(non_null) > 0:
            first_val = str(non_null.iloc[0])
            if re.match(r'\d{2}-\d{2}-\d{4}', first_val):
                col_type = "date (value date)"
    elif i == 2:
        col_type = "description"
    elif i >= 3 and i <= 4:
        # Check if contains account numbers or NaN
        if col.isna().all() or any('1090' in str(v) or '1489' in str(v) for v in non_null if pd.notna(v)):
            col_type = "account/recipient info"
        else:
            col_type = "additional info"
    elif i == 5:
        # Check if it's amount
        if len(non_null) > 0:
            first_val = str(non_null.iloc[0])
            if re.match(r'-?\d+[.,]\d+', first_val):
                col_type = "amount"
    elif i == 6:
        # Check if it's balance
        if len(non_null) > 0:
            first_val = str(non_null.iloc[0])
            if re.match(r'\d+[.,]\d+', first_val):
                col_type = "balance"
    elif i == 7:
        col_type = "index/row number"
    elif i == 8:
        col_type = "unnamed/empty"
    
    column_analysis.append({
        "index": i,
        "type": col_type,
        "non_null_count": len(non_null),
        "sample_values": [str(v) for v in sample_values[:3]]
    })
    print(f"Column {i}: {col_type} ({len(non_null)} non-null values)")

# Analyze date format
print("\n=== Date Format Analysis ===")
date_samples = df.iloc[:5, 0].dropna().tolist()
date_format = None
for date_str in date_samples:
    date_str = str(date_str).strip()
    if re.match(r'\d{2}-\d{2}-\d{4}', date_str):
        try:
            datetime.strptime(date_str, '%d-%m-%Y')
            date_format = "DD-MM-YYYY"
            break
        except:
            pass

print(f"Date format detected: {date_format}")

# Analyze currency
print("\n=== Currency Analysis ===")
currency = "PLN"  # Clearly visible in the data
print(f"Currency: {currency}")

# Analyze amount format
print("\n=== Amount Format Analysis ===")
amount_col = df.iloc[:, 5]
amount_samples = amount_col.dropna().head(10).tolist()
print(f"Amount samples: {[str(a) for a in amount_samples[:5]]}")

# Determine if positive is credit or debit
positive_count = sum(1 for a in amount_samples if isinstance(a, (int, float)) and a > 0)
negative_count = sum(1 for a in amount_samples if isinstance(a, (int, float)) and a < 0)

# Look at descriptions of positive vs negative amounts
positive_descriptions = []
negative_descriptions = []
for idx in range(min(20, len(df))):
    amount_val = df.iloc[idx, 5]
    desc_val = df.iloc[idx, 2]
    if pd.notna(amount_val) and pd.notna(desc_val):
        try:
            amount_float = float(str(amount_val).replace(',', '.'))
            if amount_float > 0:
                positive_descriptions.append(str(desc_val)[:50])
            elif amount_float < 0:
                negative_descriptions.append(str(desc_val)[:50])
        except:
            pass

print(f"\nPositive amount descriptions (sample): {positive_descriptions[:2]}")
print(f"Negative amount descriptions (sample): {negative_descriptions[:2]}")

# Positive amounts appear to be income (e.g., "PWC wynagrodzenie" = salary)
# Negative amounts appear to be expenses (e.g., "PŁATNOŚĆ KARTĄ" = card payment)
amount_positive_is = "credit"  # Income/credit

# Check if first row is header
print("\n=== Header Analysis ===")
first_row = sample_data.split('\n')[0]
print(f"First row preview: {first_row[:100]}...")
has_headers = False  # First row appears to be metadata, not column headers
skip_rows = 1  # Skip the metadata row

# Build result
result = {
    "columns_found": [f"Column {i} ({col['type']})" for i, col in enumerate(column_analysis)],
    "date_column": "Column 0",
    "description_column": "Column 2",
    "amount_column": "Column 5",
    "balance_column": "Column 6",
    "date_format": date_format,
    "currency": currency,
    "has_headers": has_headers,
    "skip_rows": skip_rows,
    "amount_positive_is": amount_positive_is,
    "questions": [
        "Column 0 appears to be the transaction/posting date, and Column 1 appears to be the value date. Which date should be used for transaction dates?",
        "The amount column uses comma as decimal separator (e.g., '10804,79', '-21,92'). The parser should convert commas to dots for numeric parsing.",
        "Some rows have account numbers in Column 4 (e.g., '72 1090 1489 0000 0000 4800 3393'). Should this information be extracted or ignored?",
        "Column 7 appears to be a row index/counter. Should this be ignored?"
    ],
    "confidence": "high"
}

# Output JSON
print("\n=== Final Analysis Result ===")
print(json.dumps(result, indent=2))

# Save to file
with open('/Users/roxsa/Documents/Devving/NumbyAI/mcp-server/santander_csv_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("\n\nAnalysis saved to santander_csv_analysis.json")
