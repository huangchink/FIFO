#!/usr/bin/env python3
import html
import sys
from pathlib import Path


SIGNALS = [
    ("tb_sync_fifo.clk", "clk"),
    ("tb_sync_fifo.rst_n", "rst_n"),
    ("tb_sync_fifo.wr_en", "wr_en"),
    ("tb_sync_fifo.rd_en", "rd_en"),
    ("tb_sync_fifo.din [7:0]", "din"),
    ("tb_sync_fifo.dout [7:0]", "dout"),
    ("tb_sync_fifo.dout_valid", "dout_valid"),
    ("tb_sync_fifo.full", "full"),
    ("tb_sync_fifo.empty", "empty"),
    ("tb_sync_fifo.dut.wr_ptr [2:0]", "wr_ptr"),
    ("tb_sync_fifo.dut.rd_ptr [2:0]", "rd_ptr"),
    ("tb_sync_fifo.g_mem_probe[0].mem_word [7:0]", "mem[0]"),
    ("tb_sync_fifo.g_mem_probe[1].mem_word [7:0]", "mem[1]"),
    ("tb_sync_fifo.g_mem_probe[2].mem_word [7:0]", "mem[2]"),
    ("tb_sync_fifo.g_mem_probe[3].mem_word [7:0]", "mem[3]"),
]


def parse_vcd(path):
    scopes = []
    vars_by_path = {}
    vars_by_id = {}
    changes = {}
    current_time = 0
    max_time = 0
    in_definitions = True

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if in_definitions:
            if line.startswith("$scope"):
                parts = line.split()
                scopes.append(parts[2])
            elif line.startswith("$upscope"):
                scopes.pop()
            elif line.startswith("$var"):
                parts = line.split()
                size = int(parts[2])
                code = parts[3]
                ref = " ".join(parts[4:-1])
                full_path = ".".join(scopes + [ref])
                vars_by_path[full_path] = {"code": code, "size": size}
                vars_by_id.setdefault(code, []).append(full_path)
                changes.setdefault(code, [])
            elif line.startswith("$enddefinitions"):
                in_definitions = False
            continue

        if line.startswith("#"):
            current_time = int(line[1:])
            max_time = max(max_time, current_time)
            continue

        if line[0] in "01xXzZ":
            value = line[0].lower()
            code = line[1:]
        elif line[0] in "bB":
            parts = line.split()
            value = parts[0][1:].lower()
            code = parts[1]
        else:
            continue

        if code in changes:
            changes[code].append((current_time, value))

    return vars_by_path, vars_by_id, changes, max_time


def display_value(value, width, label):
    if any(ch in value for ch in "xz"):
        return value

    if width == 1:
        return value

    number = int(value, 2)
    if label in ("din", "dout"):
        digits = max(1, (width + 3) // 4)
        return "0x{0:0{1}X}".format(number, digits)

    return str(number)


def value_at_zero(events):
    if not events:
        return "x"
    if events[0][0] == 0:
        return events[0][1]
    return "x"


def level_y(value, high_y, low_y, mid_y):
    if value == "1":
        return high_y
    if value == "0":
        return low_y
    return mid_y


def scalar_path(events, max_time, x0, plot_w, high_y, low_y, mid_y):
    if not events:
        return ""

    def tx(time):
        return x0 + (time / max_time) * plot_w if max_time else x0

    ordered = sorted(events)
    current = value_at_zero(ordered)
    prev_t = 0
    y = level_y(current, high_y, low_y, mid_y)
    parts = [f"M {tx(0):.1f} {y:.1f}"]

    for time, value in ordered:
        x = tx(time)
        parts.append(f"L {x:.1f} {y:.1f}")
        y = level_y(value, high_y, low_y, mid_y)
        parts.append(f"L {x:.1f} {y:.1f}")
        prev_t = time

    parts.append(f"L {tx(max_time):.1f} {y:.1f}")
    return " ".join(parts)


def vector_segments(events, max_time, x0, plot_w, y, height, width, label):
    if not events:
        return []

    def tx(time):
        return x0 + (time / max_time) * plot_w if max_time else x0

    ordered = sorted(events)
    if ordered[0][0] != 0:
        ordered = [(0, "x")] + ordered

    items = []
    for index, (time, value) in enumerate(ordered):
        next_time = ordered[index + 1][0] if index + 1 < len(ordered) else max_time
        if next_time <= time:
            continue

        x1 = tx(time)
        x2 = tx(next_time)
        w = max(1, x2 - x1)
        text = display_value(value, width, label)
        fill = "#eef4ff" if index % 2 == 0 else "#f8fbff"

        items.append(
            f'<rect x="{x1:.1f}" y="{y:.1f}" width="{w:.1f}" height="{height}" '
            f'fill="{fill}" stroke="#3973b7" stroke-width="1"/>'
        )
        if w >= 24:
            items.append(
                f'<text x="{x1 + 4:.1f}" y="{y + height - 5:.1f}" '
                f'font-size="11" fill="#17324d">{html.escape(text)}</text>'
            )

    return items


def render_svg(vars_by_path, changes, max_time, output_path):
    left = 130
    right = 30
    top = 50
    row_h = 38
    plot_w = 1220
    width = left + plot_w + right
    height = top + row_h * len(SIGNALS) + 45
    ns_max = max_time / 1000

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Consolas,Menlo,monospace}.label{font-size:13px;fill:#1d2b3a}.axis{font-size:11px;fill:#52616f}</style>',
        f'<text x="{left}" y="24" font-size="16" font-weight="700" fill="#17202a">sync_fifo simulation waveform</text>',
        f'<text x="{left}" y="42" class="axis">time: 0 ns to {ns_max:.0f} ns</text>',
    ]

    for tick_ns in range(0, int(ns_max) + 1, 50):
        x = left + (tick_ns / ns_max) * plot_w if ns_max else left
        svg.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{height - 35}" stroke="#edf1f5"/>')
        svg.append(f'<text x="{x - 10:.1f}" y="{height - 15}" class="axis">{tick_ns}</text>')

    for row, (path, label) in enumerate(SIGNALS):
        y_mid = top + row * row_h + 16
        y_top = y_mid - 9
        y_low = y_mid + 9
        y_vec = y_mid - 12
        svg.append(f'<line x1="{left}" y1="{y_mid + 18}" x2="{left + plot_w}" y2="{y_mid + 18}" stroke="#f1f3f6"/>')
        svg.append(f'<text x="16" y="{y_mid + 4}" class="label">{html.escape(label)}</text>')

        var = vars_by_path.get(path)
        if not var:
            svg.append(f'<text x="{left}" y="{y_mid + 4}" font-size="12" fill="#b00020">missing: {html.escape(path)}</text>')
            continue

        events = changes.get(var["code"], [])
        if var["size"] == 1:
            path_d = scalar_path(events, max_time, left, plot_w, y_top, y_low, y_mid)
            svg.append(f'<path d="{path_d}" fill="none" stroke="#0b5cab" stroke-width="2"/>')
        else:
            svg.extend(vector_segments(events, max_time, left, plot_w, y_vec, 24, var["size"], label))

    svg.append("</svg>")
    output_path.write_text("\n".join(svg), encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        print("usage: python tools/vcd_to_svg.py <input.vcd> <output.svg>")
        return 2

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    vars_by_path, _vars_by_id, changes, max_time = parse_vcd(input_path)
    render_svg(vars_by_path, changes, max_time, output_path)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
