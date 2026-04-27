from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NUMBERS_JSON = ROOT / "src" / "dimless" / "data" / "numbers.json"
QUANTITIES_JSON = ROOT / "src" / "dimless" / "data" / "quantities.json"
NUMBERS_OUT = ROOT / "site" / "content" / "docs" / "numbers"
QUANTITIES_OUT = ROOT / "site" / "content" / "docs" / "quantities"
DOMAINS_OUT = ROOT / "site" / "content" / "docs" / "domains"


def toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return toml_string(value)
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    raise TypeError(f"Unsupported TOML value type: {type(value)!r}")


def domain_title(domain_id: str) -> str:
    return domain_id.replace("-", " ").capitalize()


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def dim_str(dimension: list[int], dimension_order: list[str]) -> str:
    parts = []
    for sym, exp in zip(dimension_order, dimension):
        if exp == 0:
            continue
        parts.append(sym if exp == 1 else f"{sym}^{{{exp}}}")
    return r"\,".join(parts) if parts else "1"


def regime_svg(regimes: dict[str, Any]) -> str:
    raw = regimes["thresholds"]
    labels = regimes["labels"]
    descriptions = regimes.get("descriptions", [])
    colors = ["#dbeafe", "#d1fae5", "#fef9c3", "#fed7aa", "#fca5a5", "#f9a8d4"]

    # Format: [lo, t1, t2, ..., hi]  where lo=0 means "from zero", hi=null means "to infinity"
    lo_endpoint = raw[0]
    hi_endpoint = raw[-1]
    thresholds = [(t, t) if isinstance(t, (int, float)) else (t[0], t[1]) for t in raw[1:-1]]

    W = 800
    display_lo = thresholds[0][0] / 10 if lo_endpoint == 0 else float(lo_endpoint)
    display_hi = thresholds[-1][1] * 10 if hi_endpoint is None else float(hi_endpoint)

    def x(v: float) -> float:
        return (
            W
            * (math.log10(v) - math.log10(display_lo))
            / (math.log10(display_hi) - math.log10(display_lo))
        )

    TW = 240
    defs = [
        "<style>"
        ".regime .desc{visibility:hidden}"
        ".regime:hover .desc{visibility:visible}"
        ".regime:hover .bar{filter:brightness(0.85)}"
        "</style>"
    ]
    rows = []

    for i, label in enumerate(labels):
        seg_lo = display_lo if i == 0 else thresholds[i - 1][1]
        seg_hi = display_hi if i == len(labels) - 1 else thresholds[i][0]
        x0, x1 = x(seg_lo), x(seg_hi)
        w, cx = x1 - x0, (x0 + x1) / 2
        desc = descriptions[i] if i < len(descriptions) else ""
        fo_x = max(0, min(W - TW, cx - TW / 2))
        fo = (
            (
                f'<foreignObject class="desc" x="{fo_x:.0f}" y="62" width="{TW}" height="100">'
                f'<div xmlns="http://www.w3.org/1999/xhtml" style="background:white;border:1px solid #e2e8f0;'
                f'border-radius:4px;padding:6px 8px;font-size:11px;color:#475569;text-align:center">'
                f"{desc}</div></foreignObject>"
            )
            if desc
            else ""
        )
        rows.append(
            f'<g class="regime">'
            f'<rect x="{x0:.0f}" y="0" width="{w:.0f}" height="42" fill="transparent"/>'
            f'<text x="{cx:.0f}" y="14" text-anchor="middle" font-size="12" fill="#1e293b">{label}</text>'
            f'<rect class="bar" x="{x0:.0f}" y="20" width="{w:.0f}" height="20" fill="{colors[i % len(colors)]}"/>'
            f"{fo}</g>"
        )

    lo_label = f"{lo_endpoint:g}"
    rows.append(
        f'<text x="0" y="54" text-anchor="middle" font-size="10" fill="#475569">{lo_label}</text>'
    )
    if hi_endpoint is None:
        rows.append(
            f'<text x="{W}" y="54" text-anchor="middle" font-size="10" fill="#475569">∞</text>'
        )

    for i, (t_lo, t_hi) in enumerate(thresholds):
        if t_lo == t_hi:
            xt = x(t_lo)
            rows += [
                f'<line x1="{xt:.0f}" y1="18" x2="{xt:.0f}" y2="42" stroke="#475569" stroke-width="1.5"/>',
                f'<text x="{xt:.0f}" y="54" text-anchor="middle" font-size="10" fill="#475569">{t_lo:g}</text>',
            ]
        else:
            gid = f"dg{i}"
            c0, c1 = colors[i % len(colors)], colors[(i + 1) % len(colors)]
            defs.append(
                f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
                f'<stop offset="0%" stop-color="{c0}"/><stop offset="100%" stop-color="{c1}"/>'
                f"</linearGradient>"
            )
            x0, x1 = x(t_lo), x(t_hi)
            rows += [
                f'<rect x="{x0:.0f}" y="20" width="{x1 - x0:.0f}" height="20" fill="url(#{gid})"/>',
                f'<text x="{(x0 + x1) / 2:.0f}" y="54" text-anchor="middle" font-size="10" fill="#475569">{t_lo:g}–{t_hi:g}</text>',
            ]

    defs_str = f"<defs>{''.join(defs)}</defs>\n  " if defs else ""
    inner = "\n  ".join(rows)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 60" width="100%" overflow="visible"'
        f' style="font-family:sans-serif;display:block;margin:1em 0">'
        f"\n  {defs_str}{inner}\n</svg>"
    )


def latex_fraction(quantity_ids: list[str], exponents: list[int], symbols: dict[str, str]) -> str:
    def fmt_exp(a: float) -> str:
        return str(int(a)) if a == int(a) else str(a)

    def fmt_group(syms: list[str], a: float) -> str:
        body = " ".join(syms)
        if a == 1:
            return body
        if a == 0.5:
            return f"\\sqrt{{{body}}}"
        inner = f"({body})" if len(syms) > 1 else body
        return f"{inner}^{{{fmt_exp(a)}}}"

    def fmt_side(pairs: list[tuple[str, float]]) -> str:
        groups: dict[float, list[str]] = {}
        for q, a in sorted(pairs, key=lambda x: -x[1]):
            groups.setdefault(a, []).append(symbols[q])
        return " ".join(fmt_group(syms, a) for a, syms in groups.items())

    pos = [(q, e) for q, e in zip(quantity_ids, exponents) if e > 0]
    neg = [(q, abs(e)) for q, e in zip(quantity_ids, exponents) if e < 0]

    numer = fmt_side(pos) if pos else "1"
    if not neg:
        return numer
    return f"\\frac{{{numer}}}{{{fmt_side(neg)}}}"


# --- numbers ---


def write_number_page(
    number: dict[str, Any], quantities: dict[str, Any], dimension_order: list[str], out_dir: Path
) -> None:
    quantity_symbols = {qid: q["symbol"] for qid, q in quantities.items()}
    formula = latex_fraction(number["quantities"], number["exponents"], quantity_symbols)
    text_frac = f"\\frac{{\\text{{{number['numer']}}}}}{{\\text{{{number['denom']}}}}}"
    body: list[str] = []
    body += [
        f"# {number['name']}",
        "",
        f"$${number['symbol']} \\stackrel{{\\text{{def}}}}{{=}} {formula} \\sim {text_frac}$$",
        "",
        "### Quantities",
        "",
        "| Name | Symbol | Dimension |",
        "|------|--------|-----------|",
        *[
            f"| {quantities[q]['name']} | \\({quantities[q]['symbol']}\\) | \\({dim_str(quantities[q]['dimension'], dimension_order)}\\) |"
            for q in number["quantities"]
        ],
        "",
    ]
    if regimes := number.get("regimes"):
        body += ["### Regimes", "", regime_svg(regimes), ""]

    body += ["&nbsp;", "&nbsp;"]

    (out_dir / f"{number['id']}.md").write_text(
        "\n".join(
            [
                "+++",
                f"title = {toml_string(number['name'])}",
                "bookHidden = true",
                "+++",
                "",
                "\n".join(body).rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_numbers_index(numbers: list[dict[str, Any]], out_dir: Path) -> None:
    (out_dir / "_index.md").write_text(
        "\n".join(
            [
                "+++",
                'title = "Dimensionless numbers"',
                "+++",
                "",
                "# Dimensionless numbers",
                "",
                *[f"- [{n['name']}]({n['id']}/)" for n in sorted(numbers, key=lambda n: n["name"])],
                "",
            ]
        ),
        encoding="utf-8",
    )


# --- quantities ---


def write_quantity_page(
    qid: str,
    quantity: dict[str, Any],
    dimension_order: list[str],
    numbers: list[dict[str, Any]],
    out_dir: Path,
) -> None:
    body: list[str] = [
        "## Definition",
        "",
        f"- **Symbol:** {quantity['symbol']}",
        "",
        "## Dimensions",
        "",
        *[
            f"- `{dim}`: exponent `{exp}`"
            for dim, exp in zip(dimension_order, quantity["dimension"])
            if exp != 0
        ],
        "",
    ]
    used_in = [n for n in numbers if qid in n["quantities"]]
    if used_in:
        body += [
            "## Used in",
            "",
            *[
                f"- [{n['name']}](../numbers/{n['id']}/)"
                for n in sorted(used_in, key=lambda n: n["name"])
            ],
            "",
        ]

    (out_dir / f"{qid}.md").write_text(
        "\n".join(
            [
                "+++",
                f"title = {toml_string(quantity['name'])}",
                "bookHidden = true",
                "+++",
                "",
                "\n".join(body).rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_quantities_index(quantities: dict[str, Any], out_dir: Path) -> None:
    (out_dir / "_index.md").write_text(
        "\n".join(
            [
                "+++",
                'title = "Quantities"',
                "+++",
                "",
                "# Quantities",
                "",
                *[
                    f"- [{q['name']}]({qid}/)"
                    for qid, q in sorted(quantities.items(), key=lambda item: item[1]["name"])
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )


# --- domains ---


def write_domain_page(domain_id: str, numbers: list[dict[str, Any]], out_dir: Path) -> None:
    title = domain_title(domain_id)
    (out_dir / f"{domain_id}.md").write_text(
        "\n".join(
            [
                "+++",
                f"title = {toml_string(title)}",
                'type = "domain"',
                'layout = "domain"',
                "bookHidden = true",
                f"slug = {toml_string(domain_id)}",
                "+++",
                "",
                f"Dimensionless numbers in {title}.",
                "",
                "## Numbers",
                "",
                *[
                    f"- [{n['name']}](../numbers/{n['id']}/)"
                    for n in sorted(numbers, key=lambda n: n["name"])
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_domains_index(domains: dict[str, list[dict[str, Any]]], out_dir: Path) -> None:
    (out_dir / "_index.md").write_text(
        "\n".join(
            [
                "+++",
                'title = "Domains"',
                "+++",
                "",
                "# Domains",
                "",
                *[f"- [{domain_title(did)}]({did}/)" for did in sorted(domains)],
                "",
            ]
        ),
        encoding="utf-8",
    )


# --- main ---


def main() -> None:
    numbers = json.loads(NUMBERS_JSON.read_text(encoding="utf-8"))
    quantities_data = json.loads(QUANTITIES_JSON.read_text(encoding="utf-8"))
    dimension_order = quantities_data["dimension_order"]
    quantities = quantities_data["quantities"]

    reset_dir(NUMBERS_OUT)
    for number in numbers:
        write_number_page(number, quantities, dimension_order, NUMBERS_OUT)
    write_numbers_index(numbers, NUMBERS_OUT)
    print(f"Generated {len(numbers)} number pages in {NUMBERS_OUT}")

    reset_dir(QUANTITIES_OUT)
    for qid, quantity in quantities.items():
        write_quantity_page(qid, quantity, dimension_order, numbers, QUANTITIES_OUT)
    write_quantities_index(quantities, QUANTITIES_OUT)
    print(f"Generated {len(quantities)} quantity pages in {QUANTITIES_OUT}")

    domains: dict[str, list[dict[str, Any]]] = {}
    for number in numbers:
        domains.setdefault(number["domain"], []).append(number)

    reset_dir(DOMAINS_OUT)
    for domain_id, domain_numbers in domains.items():
        write_domain_page(domain_id, domain_numbers, DOMAINS_OUT)
    write_domains_index(domains, DOMAINS_OUT)
    print(f"Generated {len(domains)} domain pages in {DOMAINS_OUT}")


if __name__ == "__main__":
    main()
