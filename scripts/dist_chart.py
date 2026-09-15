#!/usr/bin/env python3
"""仟上持有人收益率分布条形图（复刻往年成品样式）。

用法（作为模块）:
    from dist_chart import draw_dist
    draw_dist(rates, "仟上私募主动优选天益1期持有人收益率分布", "/输出路径.png",
              scope="该产品", merged=False)

    rates: 收益率小数列表(0.15=15%)。
      - 分产品图: 直接用该产品sheet的「累计收益率(扣除费用)」列（单产品内一人一行=按人）
      - 合并图(全部产品/权益类): 必须先按人合并(合并收益/合并本金)再传入, 且 merged=True
    scope: 底注统计区间主语，"该产品" 或 "各产品"
    merged=True 时底注自动加"按投资者统计（同一投资者持有多只产品的合并计算）"

样式规格（勿改，与历史成品一致）:
    柱#E9A63C 标题#5A3317 底注#9A9A9A 15号字两行(第一行=公式全句铺满图宽)
    思源黑体(Source Han Sans CN) 14.2x7.0in dpi150 柱宽0.42 无y轴无网格
    分档: 暂时浮亏(有浮亏才出现)/盈利<5%/5-10%/10-15%/15-20%/20-25%/>25%, 无人的档不画
注意: 样本<5人的产品不要出分布图；浮亏占比高的产品分布图观感差，建议文字化解。
"""
import matplotlib
from datetime import date
from pathlib import Path

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ASSETS = Path(__file__).resolve().parent.parent / "assets"
for font_path in (ASSETS / "SHSCN-Regular.ttf", ASSETS / "SHSCN-Bold.ttf"):
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
if (ASSETS / "SHSCN-Regular.ttf").exists():
    plt.rcParams["font.family"] = font_manager.FontProperties(
        fname=str(ASSETS / "SHSCN-Regular.ttf")
    ).get_name()
else:
    plt.rcParams["font.family"] = "Source Han Sans CN"
plt.rcParams["axes.unicode_minus"] = False

BAR, TITLE_C, NOTE_C, AXIS_C, LABEL_C = "#E9A63C", "#5A3317", "#9A9A9A", "#C8C8C8", "#1A1A1A"

BINS = [("暂时浮亏", -99, 0), ("盈利小于5%", 0, .05), ("盈利5%-10%", .05, .10),
        ("盈利10%-15%", .10, .15), ("盈利15%-20%", .15, .20),
        ("盈利20%-25%", .20, .25), ("盈利大于25%", .25, 99)]


def _fmt(x):
    s = f"{x * 100:.2f}".rstrip("0").rstrip(".")
    return s + "%"


def dist(rates):
    if not rates:
        raise ValueError("rates 不能为空")
    return [(lab, sum(1 for v in rates if lo <= v < hi) / len(rates))
            for lab, lo, hi in BINS if sum(1 for v in rates if lo <= v < hi) > 0]


def draw_dist(rates, title, path, scope="该产品", merged=False, asof=None):
    rates = list(rates)
    data = dist(rates)
    if asof is None:
        today = date.today()
        asof = f"{today.year}年{today.month}月{today.day}日"
    line2 = f"统计区间为{scope}成立以来至{asof}。"
    if merged:
        line2 = f"按投资者统计（同一投资者持有多只产品的合并计算），统计区间为{scope}成立以来至{asof}。"
    note = ("数据来源：仟上投资，收益率指后台统计的用户累计收益率，计算公式为：累计收益率=（当前持仓资产-累计入金+累计出金）/累计入金。\n"
            + line2)

    fig, ax = plt.subplots(figsize=(14.2, 7.0), dpi=150)
    labs, vs = [d[0] for d in data], [d[1] for d in data]
    x = range(len(labs))
    ax.bar(x, vs, width=0.42, color=BAR, zorder=3)
    for i, v in enumerate(vs):
        ax.text(i, v + max(vs) * 0.03, _fmt(v), ha="center", va="bottom",
                fontsize=21, fontweight="bold", color=LABEL_C)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labs, fontsize=17, fontweight="bold", color=LABEL_C)
    ax.set_ylim(0, max(vs) * 1.22)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(AXIS_C)
    ax.spines["bottom"].set_linewidth(1.2)
    ax.tick_params(length=0)
    ax.set_title(title, fontsize=28, fontweight="bold", color=TITLE_C, pad=26)
    fig.text(0.045, 0.022, note, fontsize=15, color=NOTE_C, ha="left", va="bottom", linespacing=1.6)
    fig.subplots_adjust(left=0.045, right=0.965, top=0.86, bottom=0.22)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, facecolor="white")
    plt.close(fig)
    return str(output)


if __name__ == "__main__":
    # 冒烟测试: python3 dist_chart.py 输出 /tmp/test_dist.png
    demo = [0.12, 0.18, 0.18, 0.19, 0.22, 0.24, 0.27, -0.02]
    print(draw_dist(demo, "样式冒烟测试", "/tmp/test_dist.png"))
