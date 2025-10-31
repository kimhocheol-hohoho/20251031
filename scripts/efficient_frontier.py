"""Compute and draw the efficient frontier for temp.csv using only the standard library."""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Sequence, Tuple

DATA_FILE = Path(__file__).resolve().parent.parent / "temp.csv"
OUTPUT_FIGURE = Path(__file__).resolve().parent.parent / "figures" / "efficient_frontier.svg"
TRADING_DAYS_PER_YEAR = 252


@dataclass
class DailyRecord:
    date: datetime
    values: Dict[str, Dict[str, float]]


def load_rows(path: Path = DATA_FILE) -> List[List[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def parse_records(rows: Sequence[Sequence[str]]) -> List[DailyRecord]:
    if len(rows) < 4:
        return []

    header_metrics = rows[0]
    header_tickers = rows[1]
    indices = [
        (idx, header_metrics[idx], header_tickers[idx])
        for idx in range(1, len(header_metrics))
    ]

    records: List[DailyRecord] = []
    for raw in rows[3:]:
        if not raw or not raw[0]:
            continue
        date = datetime.strptime(raw[0], "%Y-%m-%d")
        values: Dict[str, Dict[str, float]] = {}
        for idx, metric, ticker in indices:
            if idx >= len(raw):
                continue
            field = raw[idx]
            if field:
                values.setdefault(ticker, {})[metric] = float(field)
        records.append(DailyRecord(date=date, values=values))
    return records


def build_aligned_closes(records: Iterable[DailyRecord], tickers: Sequence[str]) -> List[List[float]]:
    sorted_records = sorted(records, key=lambda r: r.date)
    aligned: List[List[float]] = []
    for record in sorted_records:
        row: List[float] = []
        for ticker in tickers:
            close = record.values.get(ticker, {}).get("Close")
            if close is None:
                row = []
                break
            row.append(close)
        if row:
            aligned.append(row)
    return aligned


def compute_returns(close_matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    returns: List[List[float]] = []
    for prev_row, curr_row in zip(close_matrix, close_matrix[1:]):
        row: List[float] = []
        for prev, curr in zip(prev_row, curr_row):
            if prev == 0:
                raise ValueError("Encountered zero close price when computing returns")
            row.append((curr - prev) / prev)
        returns.append(row)
    return returns


def transpose(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    return [list(row) for row in zip(*matrix)]


def covariance_matrix(returns: Sequence[Sequence[float]]) -> List[List[float]]:
    if not returns:
        return []
    n = len(returns)
    k = len(returns[0])
    means = [mean(column) for column in transpose(returns)]
    cov: List[List[float]] = [[0.0 for _ in range(k)] for _ in range(k)]
    for i in range(k):
        for j in range(k):
            total = 0.0
            for r in returns:
                total += (r[i] - means[i]) * (r[j] - means[j])
            cov[i][j] = total / (n - 1)
    return cov


def invert_matrix(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    n = len(matrix)
    augmented = [
        list(matrix[i]) + [1.0 if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]

    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(augmented[r][col]))
        pivot_val = augmented[pivot_row][col]
        if abs(pivot_val) < 1e-12:
            raise ValueError("Matrix is singular and cannot be inverted")
        if pivot_row != col:
            augmented[col], augmented[pivot_row] = augmented[pivot_row], augmented[col]

        pivot_val = augmented[col][col]
        scale = 1.0 / pivot_val
        augmented[col] = [v * scale for v in augmented[col]]

        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0.0:
                continue
            augmented[row] = [
                v - factor * pv
                for v, pv in zip(augmented[row], augmented[col])
            ]

    return [row[n:] for row in augmented]


def mat_vec_mul(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> List[float]:
    return [sum(m * v for m, v in zip(row, vector)) for row in matrix]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def scale_vector(vector: Sequence[float], factor: float) -> List[float]:
    return [factor * value for value in vector]


def add_vectors(a: Sequence[float], b: Sequence[float]) -> List[float]:
    return [x + y for x, y in zip(a, b)]


def efficient_frontier(
    mean_returns: Sequence[float],
    cov_matrix: Sequence[Sequence[float]],
    points: int = 50,
) -> Tuple[List[float], List[float], List[List[float]]]:
    inv_cov = invert_matrix(cov_matrix)
    ones = [1.0] * len(mean_returns)

    a = dot(ones, mat_vec_mul(inv_cov, ones))
    b = dot(ones, mat_vec_mul(inv_cov, mean_returns))
    c = dot(mean_returns, mat_vec_mul(inv_cov, mean_returns))
    d = a * c - b * b
    if abs(d) < 1e-12:
        raise ValueError("Covariance matrix leads to degenerate efficient frontier")

    min_target = min(mean_returns)
    max_target = max(mean_returns)
    if points < 2:
        points = 2
    step = (max_target - min_target) / (points - 1) if points > 1 else 0.0

    target_returns: List[float] = []
    vols: List[float] = []
    weights_list: List[List[float]] = []

    for idx in range(points):
        target = min_target + step * idx
        lam = (c - b * target) / d
        gam = (a * target - b) / d
        weights = mat_vec_mul(inv_cov, add_vectors(scale_vector(ones, lam), scale_vector(mean_returns, gam)))
        variance = dot(weights, mat_vec_mul(cov_matrix, weights))
        target_returns.append(target)
        vols.append(math.sqrt(max(variance, 0.0)))
        weights_list.append(weights)
    return target_returns, vols, weights_list


def min_variance_weights(
    mean_returns: Sequence[float], cov_matrix: Sequence[Sequence[float]]
) -> List[float]:
    inv_cov = invert_matrix(cov_matrix)
    ones = [1.0] * len(mean_returns)
    denom = dot(ones, mat_vec_mul(inv_cov, ones))
    return [value / denom for value in mat_vec_mul(inv_cov, ones)]


def annualise_statistics(returns: Sequence[Sequence[float]]) -> Tuple[List[float], List[List[float]]]:
    if not returns:
        return [], []
    mean_daily = [mean(column) for column in transpose(returns)]
    cov_daily = covariance_matrix(returns)
    mean_annual = [value * TRADING_DAYS_PER_YEAR for value in mean_daily]
    cov_annual = [
        [value * TRADING_DAYS_PER_YEAR for value in row]
        for row in cov_daily
    ]
    return mean_annual, cov_annual


def map_point(
    value: float,
    minimum: float,
    maximum: float,
    size: float,
    margin: float,
    invert: bool = False,
) -> float:
    if math.isclose(maximum, minimum):
        return margin + size / 2.0
    scaled = (value - minimum) / (maximum - minimum)
    if invert:
        scaled = 1.0 - scaled
    return margin + scaled * size


def write_svg(
    frontier_returns: Sequence[float],
    frontier_vols: Sequence[float],
    tickers: Sequence[str],
    asset_returns: Sequence[float],
    asset_vols: Sequence[float],
    min_var_point: Tuple[float, float],
) -> None:
    width, height = 800, 600
    margin = 80
    plot_width = width - 2 * margin
    plot_height = height - 2 * margin

    min_vol = min(min(frontier_vols), min(asset_vols))
    max_vol = max(max(frontier_vols), max(asset_vols))
    min_ret = min(min(frontier_returns), min(asset_returns))
    max_ret = max(max(frontier_returns), max(asset_returns))

    points = []
    for vol, ret in zip(frontier_vols, frontier_returns):
        x = map_point(vol, min_vol, max_vol, plot_width, margin)
        y = map_point(ret, min_ret, max_ret, plot_height, margin, invert=True)
        points.append(f"{x:.2f},{y:.2f}")
    frontier_path = "L".join(points[1:]) if len(points) > 1 else ""

    def axis_ticks(min_value: float, max_value: float, count: int) -> List[float]:
        if count <= 1:
            return [min_value]
        step = (max_value - min_value) / (count - 1)
        return [min_value + step * i for i in range(count)]

    x_ticks = axis_ticks(min_vol, max_vol, 5)
    y_ticks = axis_ticks(min_ret, max_ret, 5)

    svg_parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<style>text{font-family:Arial,sans-serif;font-size:14px;}" "</style>",
        "<rect x='0' y='0' width='{width}' height='{height}' fill='#ffffff' stroke='none'/>".format(width=width, height=height),
    ]

    # Axes
    x_axis_y = height - margin
    y_axis_x = margin
    svg_parts.append(
        f"<line x1='{margin}' y1='{x_axis_y}' x2='{width - margin}' y2='{x_axis_y}' stroke='#333' stroke-width='2'/>"
    )
    svg_parts.append(
        f"<line x1='{y_axis_x}' y1='{margin}' x2='{y_axis_x}' y2='{height - margin}' stroke='#333' stroke-width='2'/>"
    )

    # Grid lines and labels
    for tick in x_ticks:
        x = map_point(tick, min_vol, max_vol, plot_width, margin)
        svg_parts.append(
            f"<line x1='{x:.2f}' y1='{margin}' x2='{x:.2f}' y2='{height - margin}' stroke='#ddd' stroke-width='1'/>"
        )
        svg_parts.append(
            f"<text x='{x:.2f}' y='{height - margin + 25}' text-anchor='middle'>{tick:.2%}</text>"
        )

    for tick in y_ticks:
        y = map_point(tick, min_ret, max_ret, plot_height, margin, invert=True)
        svg_parts.append(
            f"<line x1='{margin}' y1='{y:.2f}' x2='{width - margin}' y2='{y:.2f}' stroke='#ddd' stroke-width='1'/>"
        )
        svg_parts.append(
            f"<text x='{margin - 10}' y='{y + 5:.2f}' text-anchor='end'>{tick:.2%}</text>"
        )

    # Frontier path
    if points:
        svg_parts.append(
            f"<path d='M{points[0]}{'L' + frontier_path if frontier_path else ''}' "
            "fill='none' stroke='#1f77b4' stroke-width='3'/>"
        )

    # Asset markers
    for ticker, ret, vol in zip(tickers, asset_returns, asset_vols):
        x = map_point(vol, min_vol, max_vol, plot_width, margin)
        y = map_point(ret, min_ret, max_ret, plot_height, margin, invert=True)
        svg_parts.append(
            f"<circle cx='{x:.2f}' cy='{y:.2f}' r='6' fill='#ff7f0e' stroke='none'/>"
        )
        svg_parts.append(
            f"<text x='{x + 8:.2f}' y='{y - 8:.2f}'>{ticker}</text>"
        )

    mv_x = map_point(min_var_point[0], min_vol, max_vol, plot_width, margin)
    mv_y = map_point(min_var_point[1], min_ret, max_ret, plot_height, margin, invert=True)
    svg_parts.append(
        f"<polygon points='{mv_x - 8:.2f},{mv_y:.2f} {mv_x:.2f},{mv_y - 12:.2f} {mv_x + 8:.2f},{mv_y:.2f} {mv_x:.2f},{mv_y + 12:.2f}' "
        "fill='#2ca02c' stroke='none'/>"
    )
    svg_parts.append(
        f"<text x='{mv_x + 10:.2f}' y='{mv_y + 5:.2f}'>Minimum variance</text>"
    )

    svg_parts.append(
        f"<text x='{width / 2:.2f}' y='{margin - 30}' text-anchor='middle' font-size='20'>Efficient Frontier (Annualised)</text>"
    )
    svg_parts.append(
        f"<text x='{width / 2:.2f}' y='{height - 20}' text-anchor='middle'>Annualised volatility</text>"
    )
    svg_parts.append(
        f"<text transform='translate({margin - 50},{height / 2:.2f}) rotate(-90)' text-anchor='middle'>Annualised return</text>"
    )

    svg_parts.append("</svg>")

    OUTPUT_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FIGURE.write_text("\n".join(svg_parts), encoding="utf-8")


def main() -> None:
    rows = load_rows()
    records = parse_records(rows)
    if not records:
        raise SystemExit("No records found in dataset.")

    tickers = sorted({ticker for record in records for ticker in record.values.keys()})
    close_matrix = build_aligned_closes(records, tickers)
    if len(close_matrix) < 2:
        raise SystemExit("Insufficient data to compute aligned close series.")

    daily_returns = compute_returns(close_matrix)
    if not daily_returns:
        raise SystemExit("Insufficient data to compute daily returns.")

    mean_returns, cov_matrix = annualise_statistics(daily_returns)
    target_returns, vols, weights = efficient_frontier(mean_returns, cov_matrix)
    mv_weights = min_variance_weights(mean_returns, cov_matrix)
    mv_return = dot(mv_weights, mean_returns)
    mv_vol = math.sqrt(dot(mv_weights, mat_vec_mul(cov_matrix, mv_weights)))

    asset_vols = [math.sqrt(cov_matrix[i][i]) for i in range(len(tickers))]

    write_svg(target_returns, vols, tickers, mean_returns, asset_vols, (mv_vol, mv_return))

    print("Efficient frontier summary:")
    for ticker, ret, vol in zip(tickers, mean_returns, asset_vols):
        print(f"- {ticker}: return {ret:.2%}, volatility {vol:.2%}")
    print("Minimum variance portfolio weights:")
    for ticker, weight in zip(tickers, mv_weights):
        print(f"- {ticker}: {weight:.2%}")
    print(f"Saved efficient frontier plot to {OUTPUT_FIGURE}")


if __name__ == "__main__":
    main()
