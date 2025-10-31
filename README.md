# Stock Price Summary

This repository contains a single dataset, `temp.csv`, with end-of-day pricing data for three equities:

- Samsung Electronics (005930.KS)
- Apple Inc. (AAPL)
- NVIDIA Corp. (NVDA)

Each trading day records the open, high, low, close, and volume metrics for every ticker. The file is organised with a two-row header, where the first row lists the metric and the second row lists the ticker symbol. The first column holds the trading date.

## Coverage

- **Date range:** 2023-10-16 to 2025-10-10
- **Trading days captured:** 516 rows in the file
- **Missing closes:** 34 days for 005930.KS, 17 days for AAPL, and 17 days for NVDA (those dates contain data for the other tickers but omit the listed instrument).

## Descriptive statistics

| Ticker | Avg Close | Min Close | Max Close | Avg Daily Range | Avg Volume | Best Daily Return | Worst Daily Return | Observations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 005930.KS | 66471.53 | 48968.97 | 94400.00 | 1379.43 | 19481205 | 7.21% | -10.30% | 482 |
| AAPL | 209.52 | 163.82 | 258.10 | 4.14 | 56558297 | 15.33% | -9.25% | 499 |
| NVDA | 115.60 | 40.30 | 192.57 | 4.14 | 325122505 | 18.72% | -16.97% | 499 |

**Column descriptions**

- *Avg Close / Min Close / Max Close*: Arithmetic mean, minimum, and maximum of the recorded daily closing prices.
- *Avg Daily Range*: Average of the difference between the daily high and low, a proxy for intraday volatility.
- *Avg Volume*: Mean traded shares for each symbol.
- *Best/Worst Daily Return*: Maximum and minimum one-day percentage change in the closing price within the observed period.
- *Observations*: Number of trading days with available close data for the ticker.

## Relationships and notable patterns

- Daily return correlations indicate weak co-movement between Samsung Electronics and the U.S. equities (ρ≈0.02 with AAPL and ρ≈-0.03 with NVDA), while Apple and NVIDIA show a moderate positive relationship (ρ≈0.37).
- NVIDIA exhibits the widest swing in daily closes (−16.97% to +18.72%), underscoring higher volatility relative to Apple and Samsung.
- Samsung trades with the narrowest average daily range in relative terms, but its absolute price level keeps the range over ₩1,300 per day. Apple and NVIDIA show similar average ranges in USD terms, yet NVIDIA's volume is roughly six times Apple's, reflecting heavier trading activity during the sample.

## How to reproduce the summary

All of the figures above were generated with short Python scripts using the standard library (`csv`, `datetime`, and `statistics`). You can run the same calculations by executing:

```bash
python scripts/describe.py
```

or by adapting the in-notebook examples from this README to your preferred analysis environment.
