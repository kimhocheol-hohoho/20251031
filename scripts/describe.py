"""Summarise the temp.csv dataset."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from math import sqrt
from statistics import mean
from typing import Dict, Iterable, List, Optional, Tuple

DATA_FILE = "temp.csv"


@dataclass
class DailyRecord:
    date: datetime
    values: Dict[str, Dict[str, float]]


def load_rows(path: str = DATA_FILE) -> List[List[str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def parse_records(rows: List[List[str]]) -> List[DailyRecord]:
    header_metrics = rows[0]
    header_tickers = rows[1]
    indices = [(idx, header_metrics[idx], header_tickers[idx]) for idx in range(1, len(header_metrics))]

    records: List[DailyRecord] = []
    for raw in rows[3:]:
        if not raw or not raw[0]:
            continue
        date = datetime.strptime(raw[0], "%Y-%m-%d")
        values: Dict[str, Dict[str, float]] = {}
        for idx, metric, ticker in indices:
            field = raw[idx]
            if field:
                values.setdefault(ticker, {})[metric] = float(field)
        records.append(DailyRecord(date=date, values=values))
    return records


def summarise(records: Iterable[DailyRecord]) -> Tuple[Dict[str, Dict[str, float]], Dict[str, int]]:
    history: Dict[str, Dict[str, List[float]]] = {}
    missing: Dict[str, int] = {}

    for record in records:
        for ticker, metrics in record.values.items():
            history.setdefault(ticker, {"Close": [], "High": [], "Low": [], "Open": [], "Volume": []})
            for metric, value in metrics.items():
                history[ticker][metric].append(value)

        # track missing closes by checking header-driven tickers
        for ticker in history.keys():
            if ticker not in record.values or "Close" not in record.values[ticker]:
                missing[ticker] = missing.get(ticker, 0) + 1
            else:
                missing.setdefault(ticker, 0)

    summary: Dict[str, Dict[str, float]] = {}
    for ticker, metrics in history.items():
        closes = metrics["Close"]
        highs = metrics["High"]
        lows = metrics["Low"]
        volumes = metrics["Volume"]
        returns = [
            (curr - prev) / prev
            for prev, curr in zip(closes, closes[1:])
            if prev
        ]
        summary[ticker] = {
            "avg_close": mean(closes),
            "min_close": min(closes),
            "max_close": max(closes),
            "avg_range": mean([h - l for h, l in zip(highs, lows)]),
            "avg_volume": mean(volumes),
            "best_return": max(returns) if returns else float("nan"),
            "worst_return": min(returns) if returns else float("nan"),
            "observations": float(len(closes)),
        }
    return summary, missing


def compute_return_series(records: Iterable[DailyRecord], tickers: Iterable[str]) -> Dict[str, List[float]]:
    series: Dict[str, List[Optional[float]]] = {ticker: [] for ticker in tickers}
    for record in records:
        for ticker in series:
            series[ticker].append(record.values.get(ticker, {}).get("Close"))

    returns: Dict[str, List[float]] = {}
    for ticker, closes in series.items():
        prev: Optional[float] = None
        ticker_returns: List[float] = []
        for price in closes:
            if price is None:
                prev = None
                continue
            if prev is not None:
                ticker_returns.append((price - prev) / prev)
            prev = price
        returns[ticker] = ticker_returns
    return returns


def pearson(x: List[float], y: List[float]) -> float:
    if not x or not y:
        return float("nan")
    n = min(len(x), len(y))
    if n == 0:
        return float("nan")
    x = x[:n]
    y = y[:n]
    mx = mean(x)
    my = mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denx = sqrt(sum((a - mx) ** 2 for a in x))
    deny = sqrt(sum((b - my) ** 2 for b in y))
    if denx == 0 or deny == 0:
        return float("nan")
    return num / (denx * deny)


def main() -> None:
    rows = load_rows()
    records = parse_records(rows)
    summary, missing = summarise(records)

    start = min(r.date for r in records).date()
    end = max(r.date for r in records).date()
    print(f"Date range: {start} to {end}")
    print(f"Trading days captured: {len(records)}\n")

    header = (
        "| Ticker | Avg Close | Min Close | Max Close | Avg Daily Range | Avg Volume | "
        "Best Daily Return | Worst Daily Return | Observations |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    print(header)
    print(separator)
    for ticker in sorted(summary):
        stats = summary[ticker]
        print(
            f"| {ticker} | {stats['avg_close']:.2f} | {stats['min_close']:.2f} | {stats['max_close']:.2f} | "
            f"{stats['avg_range']:.2f} | {stats['avg_volume']:.0f} | {stats['best_return']*100:.2f}% | "
            f"{stats['worst_return']*100:.2f}% | {int(stats['observations'])} |"
        )

    print("\nMissing closes:")
    for ticker in sorted(missing):
        print(f"- {ticker}: {missing[ticker]}")

    returns = compute_return_series(records, summary.keys())
    print("\nReturn correlations:")
    for a, b in combinations(sorted(summary.keys()), 2):
        corr = pearson(returns[a], returns[b])
        print(f"- {a} vs {b}: {corr:.3f}")


if __name__ == "__main__":
    main()
