import json
import math
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "dimless" / "data"
CONTENT = ROOT / "site" / "content"

NUMBERS_OUT = CONTENT / "docs" / "numbers"
QUANTITIES_OUT = CONTENT / "docs" / "quantities"
REGIME_COLORS = ["#dbeafe", "#d1fae5", "#fef9c3", "#fed7aa", "#fca5a5", "#f9a8d4"]


def load_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def write_page(path, frontmatter, body):
    lines = ["+++", *frontmatter, "+++", "", *body]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def reset_dir(path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def power_str(exponents, symbols):
    parts = [
        symbol if power == 1 else f"{symbol}^{{{power}}}"
        for symbol, power in zip(symbols, exponents)
        if power
    ]
    return r"\,".join(parts) if parts else "1"


def dim_str(dimension, dimension_order):
    return power_str(dimension, dimension_order)


def title_frontmatter(title, hidden=False):
    lines = [f"title = {json.dumps(title, ensure_ascii=False)}"]
    if hidden:
        lines.append("bookHidden = true")
    return lines


def regime_edges(thresholds):
    return [tuple(t) if isinstance(t, list) else (t, t) for t in thresholds[1:-1]]


def fmt_number(value):
    return "∞" if value is None else f"{value:g}"


def regime_ranges(regime):
    thresholds = regime["thresholds"]
    edges = regime_edges(thresholds)
    ranges = []

    for i, _label in enumerate(regime["labels"]):
        lo = thresholds[0] if i == 0 else edges[i - 1][1]
        hi = thresholds[-1] if i == len(regime["labels"]) - 1 else edges[i][0]
        ranges.append(f"{fmt_number(lo)} – {fmt_number(hi)}")

    return ranges


def regime_svg(regime):
    thresholds = regime["thresholds"]
    edges = regime_edges(thresholds)
    labels = regime["labels"]
    width = 800

    display_lo = edges[0][0] / 10 if thresholds[0] == 0 else thresholds[0]
    display_hi = edges[-1][1] * 10 if thresholds[-1] is None else thresholds[-1]

    def x(value):
        span = math.log10(display_hi) - math.log10(display_lo)
        return width * (math.log10(value) - math.log10(display_lo)) / span

    rows = []
    for i, label in enumerate(labels):
        lo = display_lo if i == 0 else edges[i - 1][1]
        hi = display_hi if i == len(labels) - 1 else edges[i][0]
        x0, x1 = x(lo), x(hi)
        rows.append(
            f'<rect x="{x0:.0f}" y="22" width="{x1 - x0:.0f}" height="20" '
            f'fill="{REGIME_COLORS[i % len(REGIME_COLORS)]}"/>'
        )
        rows.append(
            f'<text x="{(x0 + x1) / 2:.0f}" y="16" text-anchor="middle" '
            f'font-size="12" fill="#1e293b">{label}</text>'
        )

    rows.append(
        f'<text x="0" y="58" text-anchor="middle" font-size="10" '
        f'fill="#475569">{fmt_number(thresholds[0])}</text>'
    )
    rows.append(
        f'<text x="{width}" y="58" text-anchor="middle" font-size="10" '
        f'fill="#475569">{fmt_number(thresholds[-1])}</text>'
    )

    for lo, hi in edges:
        tick = x(lo)
        label = fmt_number(lo) if lo == hi else f"{fmt_number(lo)}–{fmt_number(hi)}"
        if lo != hi:
            tick = (x(lo) + x(hi)) / 2
        rows.append(
            f'<line x1="{tick:.0f}" y1="20" x2="{tick:.0f}" y2="44" '
            f'stroke="#475569" stroke-width="1"/>'
        )
        rows.append(
            f'<text x="{tick:.0f}" y="58" text-anchor="middle" font-size="10" '
            f'fill="#475569">{label}</text>'
        )

    rows_html = "\n  ".join(rows)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 64" '
        f'width="100%" overflow="visible" '
        f'style="font-family:sans-serif;display:block;margin:1em 0">'
        f"\n  {rows_html}\n</svg>"
    )


def tex_exp(power):
    return str(int(power)) if power == int(power) else str(power)


def tex_term(symbol, power):
    if power == 1:
        return symbol
    if power == 0.5:
        return f"\\sqrt{{{symbol}}}"
    if " " in symbol:
        symbol = f"({symbol})"
    return f"{symbol}^{{{tex_exp(power)}}}"


def tex_product(quantities, exponents, symbols):
    top = []
    bottom = []
    for qid, power in zip(quantities, exponents):
        target = top if power > 0 else bottom
        target.append((symbols[qid], abs(power)))

    def render(items):
        groups = {}
        for symbol, power in items:
            groups.setdefault(power, []).append(symbol)
        return " ".join(
            tex_term(" ".join(groups[power]), power) for power in sorted(groups, reverse=True)
        )

    result = render(top) or "1"
    if bottom:
        result += "/" + "/".join(tex_term(symbol, power) for symbol, power in bottom)
    return result


def latex_fraction(numer, denom, symbols):
    n = tex_product(numer["quantities"], numer["exponents"], symbols)
    if not denom["quantities"]:
        return n
    d = tex_product(denom["quantities"], denom["exponents"], symbols)
    return f"\\frac{{{n}}}{{{d}}}"


def aliases_text(number):
    aliases = number.get("aliases", [])
    if not aliases:
        return ""
    return ", ".join(aliases)


def si_units_text(quantity, si_unit_order):
    return power_str(quantity["si_units"], si_unit_order)


def number_page(number, quantities, dimension_order, si_unit_order):
    symbols = {qid: quantity["symbol"] for qid, quantity in quantities.items()}
    numer = number["numer"]
    denom = number["denom"]
    used_quantities = list(dict.fromkeys(numer["quantities"] + denom["quantities"]))
    text_fraction = f"\\frac{{\\text{{{numer['label']}}}}}{{\\text{{{denom['label']}}}}}"

    body = [
        f"# {number['name']}",
        "",
    ]

    if aliases := aliases_text(number):
        body.extend([f"Also known as: {aliases}.", ""])

    body.extend(
        [
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;'
            'padding:1rem 1.5rem;margin:1rem 0;text-align:center">',
            "",
            f"$${number['symbol']} \\stackrel{{\\text{{def}}}}{{=}} "
            f"{latex_fraction(numer, denom, symbols)} \\sim {text_fraction}$$",
            "",
            "</div>",
            "",
            "### Quantities",
            "",
            "| Name | Symbol | SI units | Dimension |",
            "|------|--------|----------|-----------|",
        ]
    )

    for qid in used_quantities:
        quantity = quantities[qid]
        dim = dim_str(quantity["dimension"], dimension_order)
        body.append(
            f"| {quantity['name']} | \\({quantity['symbol']}\\) | "
            f"\\({si_units_text(quantity, si_unit_order)}\\) | \\({dim}\\) |"
        )

    if number.get("regimes"):
        body.extend(["", "### Regimes", ""])
        for name, regime in number["regimes"].items():
            body.extend(
                [
                    f"**{name.capitalize()}**",
                    "",
                    regime_svg(regime),
                    "",
                    "| Range | Regime | Description |",
                    "|-------|--------|-------------|",
                ]
            )
            descriptions = regime.get("descriptions", [""] * len(regime["labels"]))
            for label, rng, desc in zip(regime["labels"], regime_ranges(regime), descriptions):
                body.append(f"| {rng} | {label} | {desc} |")
            body.append("")

    return body + ["&nbsp;", "&nbsp;"]


def quantity_page(qid, quantity, numbers, dimension_order):
    body = [
        f"# {quantity['name']}",
        "",
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;'
        'padding:1rem 1.5rem;margin:1rem 0;text-align:center">',
        "",
        f"$${quantity['symbol']} \\sim {dim_str(quantity['dimension'], dimension_order)}$$",
        "",
        "</div>",
        "",
    ]

    if quantity.get("description"):
        body.extend([quantity["description"], ""])

    used_in = [
        number
        for number in numbers
        if qid in number["numer"]["quantities"] or qid in number["denom"]["quantities"]
    ]
    if used_in:
        body.extend(["### Used in", ""])
        for number in sorted(used_in, key=lambda item: item["name"]):
            body.append(f"- [{number['name']}](../numbers/{number['id']}/)")
        body.append("")

    return body + ["&nbsp;", "&nbsp;"]


def stat_box(value, label, middle=False):
    border = ""
    if middle:
        border = "border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;"
    return (
        f'    <div style="padding:1rem 2.5rem;{border}">'
        f'<div style="font-size:2rem;font-weight:700;color:#1e293b">{value}</div>'
        f'<div style="font-size:0.8rem;color:#64748b;margin-top:0.2rem">{label}</div>'
        "</div>"
    )


def home_page(numbers, quantities):
    domains = {number["domain"] for number in numbers}
    return [
        '<img src="logo.svg" alt="Logo" style="display:block;margin:2rem auto 1rem;width:96px;height:96px;">',
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
        '  <div style="display:inline-flex;border:1px solid #e2e8f0;border-radius:8px;'
        'overflow:hidden;text-align:center">',
        stat_box(len(numbers), "numbers"),
        stat_box(len(quantities), "quantities", middle=True),
        stat_box(len(domains), "domains"),
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
        "<b>AI use disclaimer:</b> ChatGPT 5.5 was used to help write and generate some of the "
        "content on this website. All output was reviewed and edited by a human before "
        "being published.",
    ]


def numbers_index(numbers):
    by_domain = {}
    for number in numbers:
        by_domain.setdefault(number["domain"], []).append(number)

    body = ["# Dimensionless numbers", ""]
    for domain, domain_numbers in sorted(by_domain.items()):
        body.extend([f"## {domain.replace('-', ' ').capitalize()}", ""])
        for number in sorted(domain_numbers, key=lambda item: item["name"]):
            aliases = aliases_text(number)
            suffix = f" ({aliases})" if aliases else ""
            body.append(f"- [{number['name']}]({number['id']}/){suffix}")
        body.append("")
    return body


def quantities_index(quantities):
    body = ["# Quantities", ""]
    for qid, quantity in sorted(quantities.items(), key=lambda item: item[1]["name"]):
        body.append(f"- [{quantity['name']}]({qid}/)")
    return body + [""]


def main():
    numbers = load_json("numbers.json")
    quantities_data = load_json("quantities.json")
    quantities = quantities_data["quantities"]
    dimension_order = quantities_data["dimension_order"]
    si_unit_order = quantities_data["si_unit_order"]

    write_page(
        CONTENT / "_index.md",
        title_frontmatter("Encyclopedia of dimensionless numbers"),
        home_page(numbers, quantities),
    )

    reset_dir(NUMBERS_OUT)
    for number in numbers:
        write_page(
            NUMBERS_OUT / f"{number['id']}.md",
            title_frontmatter(number["name"], hidden=True),
            number_page(number, quantities, dimension_order, si_unit_order),
        )
    write_page(
        NUMBERS_OUT / "_index.md",
        title_frontmatter("Dimensionless numbers"),
        numbers_index(numbers),
    )
    print(f"Generated {len(numbers)} number pages in {NUMBERS_OUT}")

    reset_dir(QUANTITIES_OUT)
    for qid, quantity in quantities.items():
        write_page(
            QUANTITIES_OUT / f"{qid}.md",
            title_frontmatter(quantity["name"], hidden=True),
            quantity_page(qid, quantity, numbers, dimension_order),
        )
    write_page(
        QUANTITIES_OUT / "_index.md",
        title_frontmatter("Quantities"),
        quantities_index(quantities),
    )
    print(f"Generated {len(quantities)} quantity pages in {QUANTITIES_OUT}")


if __name__ == "__main__":
    main()
