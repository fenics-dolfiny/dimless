from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NUMBERS_JSON = ROOT / "src" / "dimless" / "data" / "numbers.json"
QUANTITIES_JSON = ROOT / "src" / "dimless" / "data" / "quantities.json"
HOME_OUT = ROOT / "site" / "content" / "_index.md"
NUMBERS_OUT = ROOT / "site" / "content" / "docs" / "numbers"
QUANTITIES_OUT = ROOT / "site" / "content" / "docs" / "quantities"


def toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def domain_title(domain_id: str) -> str:
    return domain_id.replace("-", " ").capitalize()


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def write_page(path: Path, frontmatter: list[str], body: list[str]) -> None:
    lines = ["+++", *frontmatter, "+++", "", *body]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


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
    lo_endpoint, hi_endpoint = raw[0], raw[-1]
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
        "<style>.regime .desc{visibility:hidden}.regime:hover .desc{visibility:visible}.regime:hover .bar{filter:brightness(0.85)}</style>"
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

    rows.append(
        f'<text x="0" y="54" text-anchor="middle" font-size="10" fill="#475569">{lo_endpoint:g}</text>'
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


def write_number_page(
    number: dict[str, Any], quantities: dict[str, Any], dimension_order: list[str], out_dir: Path
) -> None:
    quantity_symbols = {qid: q["symbol"] for qid, q in quantities.items()}
    formula = latex_fraction(number["quantities"], number["exponents"], quantity_symbols)
    text_frac = f"\\frac{{\\text{{{number['numer']}}}}}{{\\text{{{number['denom']}}}}}"
    body = [
        f"# {number['name']}",
        "",
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:1rem 1.5rem;margin:1rem 0;text-align:center">',
        "",
        f"$${number['symbol']} \\stackrel{{\\text{{def}}}}{{=}} {formula} \\sim {text_frac}$$",
        "",
        "</div>",
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
    write_page(
        out_dir / f"{number['id']}.md",
        [f"title = {toml_string(number['name'])}", "bookHidden = true"],
        body,
    )


def write_home_page(
    numbers: list[dict[str, Any]], quantities: dict[str, Any], domains: dict[str, Any]
) -> None:
    n_numbers = len(numbers)
    n_quantities = len(quantities)
    n_domains = len(domains)
    write_page(
        HOME_OUT,
        ['title = "Encyclopedia of dimensionless numbers"'],
        [
            '<img src="/logo.svg" alt="Logo" style="display:block;margin:2rem auto 1rem;width:96px;height:96px;">',
            "",
            "# Encyclopedia of dimensionless numbers",
            "",
            "Dimensionless numbers appear throughout science and engineering whenever a physical",
            "phenomenon can be characterised by the ratio of two competing effects — inertia versus",
            "viscosity, convection versus conduction, oscillation versus transport. Because they carry",
            "no units, the same number describes the same physical balance regardless of the scale or",
            "the working fluid, making them the natural language of similarity, scaling, and",
            "dimensional analysis.",
            "",
            "**Current database**",
            "",
            '<div style="display:flex;justify-content:center;margin:1.5rem 0">',
            '  <div style="display:inline-flex;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;text-align:center">',
            f'    <div style="padding:1rem 2.5rem"><div style="font-size:2rem;font-weight:700;color:#1e293b">{n_numbers}</div><div style="font-size:0.8rem;color:#64748b;margin-top:0.2rem">numbers</div></div>',
            f'    <div style="padding:1rem 2.5rem;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0"><div style="font-size:2rem;font-weight:700;color:#1e293b">{n_quantities}</div><div style="font-size:0.8rem;color:#64748b;margin-top:0.2rem">quantities</div></div>',
            f'    <div style="padding:1rem 2.5rem"><div style="font-size:2rem;font-weight:700;color:#1e293b">{n_domains}</div><div style="font-size:0.8rem;color:#64748b;margin-top:0.2rem">domains</div></div>',
            "  </div>",
            "</div>",
            "",
            "For each number you will find its definition as a ratio of named physical quantities,",
            "the physical interpretation of numerator and denominator, the dimensions of every",
            "quantity involved, and - where applicable - the flow regimes the number delineates.",
            "Each quantity links back to the numbers that use it.",
            "",
            "Explore all [numbers](docs/numbers/) or look up individual [quantities](docs/quantities/).",
            "",
        ],
    )


def write_numbers_index(numbers: list[dict[str, Any]], out_dir: Path) -> None:
    domains: dict[str, list[dict[str, Any]]] = {}
    for n in numbers:
        domains.setdefault(n["domain"], []).append(n)
    body: list[str] = ["# Dimensionless numbers", ""]
    for domain_id in sorted(domains):
        body += [f"## {domain_title(domain_id)}", ""]
        body += [
            f"- [{n['name']}]({n['id']}/)"
            for n in sorted(domains[domain_id], key=lambda n: n["name"])
        ]
        body += [""]
    write_page(out_dir / "_index.md", ['title = "Dimensionless numbers"'], body)


def write_quantity_page(
    qid: str,
    quantity: dict[str, Any],
    dimension_order: list[str],
    numbers: list[dict[str, Any]],
    out_dir: Path,
) -> None:
    body = [
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
    write_page(
        out_dir / f"{qid}.md",
        [f"title = {toml_string(quantity['name'])}", "bookHidden = true"],
        body,
    )


def write_quantities_index(quantities: dict[str, Any], out_dir: Path) -> None:
    write_page(
        out_dir / "_index.md",
        ['title = "Quantities"'],
        [
            "# Quantities",
            "",
            *[
                f"- [{q['name']}]({qid}/)"
                for qid, q in sorted(quantities.items(), key=lambda item: item[1]["name"])
            ],
            "",
        ],
    )


def main() -> None:
    numbers = json.loads(NUMBERS_JSON.read_text(encoding="utf-8"))
    quantities_data = json.loads(QUANTITIES_JSON.read_text(encoding="utf-8"))
    dimension_order = quantities_data["dimension_order"]
    quantities = quantities_data["quantities"]

    domains: dict[str, list[dict[str, Any]]] = {}
    for number in numbers:
        domains.setdefault(number["domain"], []).append(number)

    write_home_page(numbers, quantities, domains)

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


if __name__ == "__main__":
    main()
