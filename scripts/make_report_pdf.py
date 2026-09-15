#!/usr/bin/env python3
"""仟上私募报告 markdown → 成品PDF（复刻2025年终总结版式）。
用法: python3 make_report_pdf.py 输入.md 输出.pdf [--title 封面大标题]
版式: 每页页眉logo条+页脚页码+45°斜向水印; P1封面; P2目录(自动页码); P3起正文。
"""
import re, os, argparse
from datetime import date
from pathlib import Path
import fitz
import markdown as mdlib
from matplotlib import font_manager as fm
from matplotlib.font_manager import FontProperties

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
IMGDIR = None
ORANGE = "#C25A12"; BROWN = "#5A3317"; GOLD = (0.72, 0.55, 0.25)
WATERMARK = "本文件不得转载或向第三方传阅"
PAGE = fitz.paper_rect("a4")            # 595x842
BODY = fitz.Rect(60, 85, 535, 775)      # 正文区

FONT_R = os.path.join(ASSETS, "SHSCN-Regular.ttf")   # OTF经otf2ttf转换,PyMuPDF只认TTF
FONT_B = os.path.join(ASSETS, "SHSCN-Bold.ttf")

# 配图占位 → 实际图片（有实图的插图，没有的保留灰色占位行）
IMG_MAP = {
    "权益类产品持有人收益率分布": "权益类产品-收益率分布.png",
    "主动优选天益1期持有人收益率分布": "主动优选天益1期-收益率分布.png",
}


def md_to_html(md_text):
    # 去掉发布前删除的备注节
    md_text = re.split(r"^## 修订备注", md_text, flags=re.M)[0]
    # 去掉文首 H1 与版本引用块（封面单独画）
    md_text = re.sub(r"^# .*?\n(> .*\n)*", "", md_text, count=1)
    # 配图占位处理
    def repl(m):
        inner = m.group(1)
        for k, f in IMG_MAP.items():
            if k in inner:
                return f'<div class="img"><img src="{f}"></div>'
        return f'<p class="ph">{inner}</p>'
    md_text = re.sub(r"^> (【配图[:：][^\n]*】.*)$", repl, md_text, flags=re.M)
    html = mdlib.markdown(md_text, extensions=["tables"])
    return html


CSS = f"""
@font-face {{ font-family: shs;  src: url(SHSCN-Regular.ttf); }}
@font-face {{ font-family: shsb; src: url(SHSCN-Bold.ttf); }}
body {{ font-family: shs; font-size: 10.5pt; line-height: 1.75; color: #222222; }}
h2 {{ font-family: shsb; font-size: 16pt; color: {BROWN}; margin-top: 18px; }}
h3 {{ font-family: shsb; font-size: 13.5pt; color: {ORANGE}; margin-top: 14px; }}
h4 {{ font-family: shsb; font-size: 11.5pt; color: #222222; margin-top: 10px; }}
b, strong {{ font-family: shsb; color: {ORANGE}; }}
blockquote {{ color: #6E5D46; font-size: 9.5pt; margin-left: 10px; }}
p.ph {{ color: #999999; font-size: 9pt; }}
div.img {{ text-align: center; }}
img {{ width: 440px; }}
table {{ border-collapse: collapse; font-size: 9.5pt; }}
td, th {{ border: 0.5pt solid #C8B89A; padding: 3px 8px; }}
th {{ font-family: shsb; background-color: #FBF4E6; }}
li {{ margin: 2px 0; }}
"""


def render_story(html, css, out_path, heads):
    ar = fitz.Archive()
    ar.add(str(Path(FONT_R).parent))
    if IMGDIR and Path(IMGDIR).is_dir():
        ar.add(str(IMGDIR))
    story = fitz.Story(html=html, user_css=css, archive=ar)
    writer = fitz.DocumentWriter(out_path)
    pno = 0
    more = 1
    while more:
        dev = writer.begin_page(PAGE)
        more, _ = story.place(BODY)
        def _make_cb(_page):
            def _cb(pos):
                if pos.open_close == 1 and pos.heading and pos.text:
                    heads.append((pos.heading, pos.text, _page))
            return _cb
        story.element_positions(_make_cb(pno))
        story.draw(dev)
        writer.end_page()
        pno += 1
    writer.close()
    return pno


def decorate(doc, title_for_footer=""):
    logo = os.path.join(ASSETS, "header_logo.png")
    f_wm = fitz.Font(fontfile=FONT_B)
    f_pg = fitz.Font(fontfile=FONT_R)
    for i, page in enumerate(doc):
        # 页眉logo条(复刻去年位置)
        if os.path.exists(logo):
            page.insert_image(fitz.Rect(90, 36, 505, 61), filename=logo)
        # 页脚页码
        tw = fitz.TextWriter(page.rect)
        s = str(i + 1)
        w = f_pg.text_length(s, fontsize=9)
        tw.append(((PAGE.width - w) / 2, 815), s, font=f_pg, fontsize=9)
        tw.write_text(page, color=(0.4, 0.4, 0.4))
        # 45°斜向水印
        wm = fitz.TextWriter(page.rect)
        wlen = f_wm.text_length(WATERMARK, fontsize=26)
        center = fitz.Point(PAGE.width / 2, PAGE.height / 2)
        start = fitz.Point(center.x - wlen / 2, center.y)
        wm.append(start, WATERMARK, font=f_wm, fontsize=26)
        mat = fitz.Matrix(-42)
        wm.write_text(page, color=(0.55, 0.5, 0.45), opacity=0.13,
                      morph=(center, mat))


def build_cover(doc, title, subtitle):
    page = doc.new_page(pno=0, width=PAGE.width, height=PAGE.height)
    hex2rgb = lambda h: tuple(int(h[i:i+2], 16) / 255 for i in (1, 3, 5))
    tw = fitz.TextWriter(page.rect)
    fb = fitz.Font(fontfile=FONT_B); fr = fitz.Font(fontfile=FONT_R)
    # 大标题(自动换行居中, 简化: 手动二分)
    size = 26
    if fb.text_length(title, size) < 440:
        lines = [title]
    elif "暨" in title:
        i = title.index("暨") + 1
        lines = [title[:i], title[i:]]
    else:
        lines = [title[:len(title)//2], title[len(title)//2:]]
    y = 300
    for ln in lines:
        w = fb.text_length(ln, size)
        tw.append(((PAGE.width - w) / 2, y), ln, font=fb, fontsize=size)
        y += 44
    tw.write_text(page, color=hex2rgb(BROWN))
    tw2 = fitz.TextWriter(page.rect)
    w = fr.text_length(subtitle, 12)
    tw2.append(((PAGE.width - w) / 2, y + 30), subtitle, font=fr, fontsize=12)
    tw2.write_text(page, color=(0.45, 0.4, 0.35))


def build_toc_page(doc, heads, offset):
    """heads: [(level, text, story_page)] -> 目录页(插在index=1)"""
    page = doc.new_page(pno=1, width=PAGE.width, height=PAGE.height)
    hex2rgb = lambda h: tuple(int(h[i:i+2], 16) / 255 for i in (1, 3, 5))
    fb = fitz.Font(fontfile=FONT_B); fr = fitz.Font(fontfile=FONT_R)
    tw = fitz.TextWriter(page.rect)
    w = fb.text_length("目录", 18)
    tw.append(((PAGE.width - w) / 2, 120), "目录", font=fb, fontsize=18)
    tw.write_text(page, color=hex2rgb(BROWN))
    y = 165
    shape = page.new_shape()
    for lvl, text, spage in heads:
        if lvl > 3 or y > 760:
            continue
        indent = 70 if lvl == 2 else 95
        fnt = fb if lvl == 2 else fr
        size = 11.5 if lvl == 2 else 10.5
        pno = str(spage + 1 + offset)
        t = fitz.TextWriter(page.rect)
        t.append((indent, y), text[:38], font=fnt, fontsize=size)
        pw = fr.text_length(pno, size)
        t.append((525 - pw, y), pno, font=fr, fontsize=size)
        t.write_text(page, color=hex2rgb(BROWN) if lvl == 2 else (0.2, 0.2, 0.2))
        shape.draw_line(fitz.Point(indent + fnt.text_length(text[:38], size) + 8, y),
                        fitz.Point(518 - pw, y))
        y += 24 if lvl == 2 else 21
    shape.finish(color=(0.75, 0.7, 0.6), width=0.5, dashes="[1 3] 0")
    shape.commit()


def main():
    global ASSETS, IMGDIR, FONT_R, FONT_B
    ap = argparse.ArgumentParser()
    ap.add_argument("md"); ap.add_argument("out")
    ap.add_argument("--title", default="仟上私募定期运作总结报告")
    ap.add_argument("--subtitle", help="封面副标题；默认使用当天日期")
    ap.add_argument("--assets-dir", help="字体和Logo目录；默认使用Skill内assets目录")
    ap.add_argument("--image-dir", help="配图目录；默认使用输入Markdown所在目录")
    a = ap.parse_args()

    ASSETS = Path(a.assets_dir).expanduser().resolve() if a.assets_dir else SKILL_DIR / "assets"
    IMGDIR = Path(a.image_dir).expanduser().resolve() if a.image_dir else Path(a.md).expanduser().resolve().parent
    if not a.subtitle:
        today = date.today()
        a.subtitle = f"数据截止：{today.year}年{today.month}月{today.day}日"
    FONT_R = str(ASSETS / "SHSCN-Regular.ttf")
    FONT_B = str(ASSETS / "SHSCN-Bold.ttf")
    missing = [str(path) for path in (Path(FONT_R), Path(FONT_B), ASSETS / "header_logo.png") if not path.exists()]
    if missing:
        raise SystemExit("缺少PDF资源文件: " + ", ".join(missing))

    html = md_to_html(Path(a.md).read_text(encoding="utf-8"))
    heads = []
    tmp = a.out + ".body.pdf"
    render_story(html, CSS, tmp, heads)

    doc = fitz.open(tmp)
    build_cover(doc, a.title, a.subtitle)          # 插在0 → 正文后移1
    build_toc_page(doc, heads, offset=2)           # 插在1 → 正文共后移2
    decorate(doc)
    # PDF书签
    toc_heads = [(lvl, text, spage) for lvl, text, spage in heads if lvl <= 3]
    if toc_heads:
        base_level = min(lvl for lvl, _, _ in toc_heads)
        toc = [[lvl - base_level + 1, text, spage + 3]
               for lvl, text, spage in toc_heads]
        doc.set_toc(toc)
    doc.save(a.out, deflate=True, garbage=3)
    doc.close(); os.remove(tmp)
    with fitz.open(a.out) as result:
        page_count = result.page_count
    print(f"完成: {a.out}  共{page_count}页, 目录条目{len([h for h in heads if h[0]<=3])}个")


if __name__ == "__main__":
    main()
