# -*- coding: utf-8 -*-
"""生成教材数据集可视化展示页 showcase.html"""
import csv, os, io, base64, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "课程教材总表.csv")
COVERS = os.path.join(ROOT, "covers")
OUT = os.path.join(ROOT, "showcase.html")

rows = list(csv.DictReader(io.open(CSV, encoding="utf-8-sig")))

# 去重教材，收集信息
books = {}
for r in rows:
    b = (r.get("教材名称") or "").strip()
    if not b: continue
    if b not in books:
        books[b] = {
            "name": b,
            "author": r.get("主编",""),
            "edition": r.get("版次",""),
            "publisher": r.get("出版社",""),
            "isbn": r.get("ISBN",""),
            "colleges": set(),
            "majors": set(),
        }
    if r.get("学院"): books[b]["colleges"].add(r["学院"])
    if r.get("专业"): books[b]["majors"].add(r["专业"])

# 找封面文件
cover_map = {}
for f in os.listdir(COVERS):
    if f.endswith((".jpg",".png")):
        # 文件名格式: ISBN_书名.jpg
        parts = f.split("_", 1)
        if len(parts) == 2:
            isbn = parts[0]
            cover_map[isbn] = f

book_list = []
for b in books.values():
    cover_file = cover_map.get(b["isbn"], "")
    cover_path = os.path.join(COVERS, cover_file) if cover_file else ""
    cover_b64 = ""
    if cover_path and os.path.exists(cover_path):
        with open(cover_path, "rb") as f:
            cover_b64 = base64.b64encode(f.read()).decode()
    book_list.append({
        "name": b["name"],
        "author": b["author"],
        "edition": b["edition"],
        "publisher": b["publisher"],
        "isbn": b["isbn"],
        "colleges": sorted(b["colleges"]),
        "majors_count": len(b["majors"]),
        "cover": cover_b64,
        "has_cover": bool(cover_b64),
    })

# 按学院分组统计
college_stats = {}
for r in rows:
    c = r.get("学院","")
    if not c: continue
    if c not in college_stats:
        college_stats[c] = {"courses": 0, "with_textbook": 0, "with_isbn": 0}
    college_stats[c]["courses"] += 1
    if r.get("教材名称"): college_stats[c]["with_textbook"] += 1
    if r.get("ISBN"): college_stats[c]["with_isbn"] += 1

total_courses = len(rows)
total_with_book = sum(1 for r in rows if r.get("教材名称"))
total_with_isbn = sum(1 for r in rows if r.get("ISBN"))
total_covers = sum(1 for b in book_list if b["has_cover"])

books_json = json.dumps(book_list, ensure_ascii=False)
colleges_json = json.dumps(
    [{"name":k, **v} for k,v in sorted(college_stats.items(), key=lambda x:-x[1]["with_textbook"])],
    ensure_ascii=False
)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>华中农业大学本科教材数据集 · 效果展示</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background:#f5f7fa; color:#333; }}
.header {{ background: linear-gradient(135deg, #1a5632 0%, #2d8a4e 100%); color:#fff; padding:48px 24px; text-align:center; }}
.header h1 {{ font-size:32px; margin-bottom:8px; }}
.header p {{ font-size:16px; opacity:0.9; }}
.stats {{ display:flex; justify-content:center; gap:32px; margin-top:28px; flex-wrap:wrap; }}
.stat {{ background:rgba(255,255,255,0.15); border-radius:12px; padding:16px 28px; min-width:140px; }}
.stat .num {{ font-size:36px; font-weight:700; }}
.stat .label {{ font-size:13px; opacity:0.85; margin-top:4px; }}
.container {{ max-width:1400px; margin:0 auto; padding:32px 20px; }}
.section-title {{ font-size:22px; font-weight:700; margin:32px 0 16px; color:#1a5632; border-left:4px solid #2d8a4e; padding-left:12px; }}
.filter-bar {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px; }}
.filter-btn {{ padding:6px 16px; border-radius:20px; border:1px solid #ccc; background:#fff; cursor:pointer; font-size:13px; transition:all 0.2s; }}
.filter-btn:hover {{ border-color:#2d8a4e; color:#2d8a4e; }}
.filter-btn.active {{ background:#2d8a4e; color:#fff; border-color:#2d8a4e; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:20px; }}
.card {{ background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08); transition:transform 0.2s, box-shadow 0.2s; cursor:pointer; }}
.card:hover {{ transform:translateY(-4px); box-shadow:0 8px 24px rgba(0,0,0,0.15); }}
.card .cover {{ width:100%; height:280px; object-fit:cover; background:#eee; display:flex; align-items:center; justify-content:center; }}
.card .cover img {{ width:100%; height:100%; object-fit:cover; }}
.card .no-cover {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#e8f5e9,#c8e6c9); color:#66bb6a; font-size:14px; text-align:center; padding:12px; }}
.card .info {{ padding:12px 14px; }}
.card .title {{ font-size:14px; font-weight:600; line-height:1.4; margin-bottom:6px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; min-height:40px; }}
.card .meta {{ font-size:12px; color:#888; line-height:1.6; }}
.card .isbn {{ font-size:11px; color:#2d8a4e; font-family:monospace; margin-top:4px; }}
.card .badge {{ display:inline-block; background:#e8f5e9; color:#2d8a4e; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; }}
table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
th, td {{ padding:10px 14px; text-align:left; font-size:13px; border-bottom:1px solid #eee; }}
th {{ background:#1a5632; color:#fff; font-weight:600; }}
tr:hover {{ background:#f5f7fa; }}
.progress {{ height:8px; background:#e0e0e0; border-radius:4px; overflow:hidden; }}
.progress-bar {{ height:100%; background:linear-gradient(90deg,#2d8a4e,#66bb6a); border-radius:4px; }}
.footer {{ text-align:center; padding:32px; color:#999; font-size:12px; }}
</style>
</head>
<body>
<div class="header">
  <h1>华中农业大学本科教材数据集</h1>
  <p>基于 2025 版人才培养方案 · 覆盖全部本科专业 · 含高清封面与 ISBN</p>
  <div class="stats">
    <div class="stat"><div class="num">{total_courses}</div><div class="label">课程记录总数</div></div>
    <div class="stat"><div class="num">{total_with_book}</div><div class="label">已配教材课程</div></div>
    <div class="stat"><div class="num">{total_with_isbn}</div><div class="label">已填 ISBN</div></div>
    <div class="stat"><div class="num">{total_covers}</div><div class="label">高清封面</div></div>
  </div>
</div>
<div class="container">
  <div class="section-title">各学院教材覆盖情况</div>
  <table>
    <thead><tr><th>学院</th><th>课程总数</th><th>已配教材</th><th>已填 ISBN</th><th>教材覆盖率</th></tr></thead>
    <tbody id="collegeTable"></tbody>
  </table>
  <div class="section-title">教材封面画廊（共 {len(book_list)} 本）</div>
  <div class="filter-bar" id="filterBar"></div>
  <div class="grid" id="bookGrid"></div>
</div>
<div class="footer">华中农业大学本科教材数据集 · 数据来源：2025版人才培养方案 + 豆瓣读书 · 仅供学习参考</div>
<script>
const books = {books_json};
const colleges = {colleges_json};
// 学院表
const tb = document.getElementById('collegeTable');
colleges.forEach(c => {{
  const pct = c.courses > 0 ? (c.with_textbook/c.courses*100).toFixed(1) : 0;
  tb.innerHTML += `<tr><td>${{c.name}}</td><td>${{c.courses}}</td><td>${{c.with_textbook}}</td><td>${{c.with_isbn}}</td>
  <td><div style="display:flex;align-items:center;gap:8px;"><div class="progress" style="flex:1;"><div class="progress-bar" style="width:${{pct}}%"></div></div><span>${{pct}}%</span></div></td></tr>`;
}});
// 筛选
const allColleges = [...new Set(books.flatMap(b => b.colleges))].sort();
const fb = document.getElementById('filterBar');
fb.innerHTML = '<button class="filter-btn active" data-c="">全部</button>' + allColleges.map(c => `<button class="filter-btn" data-c="${{c}}">${{c}}</button>`).join('');
fb.addEventListener('click', e => {{
  if (!e.target.classList.contains('filter-btn')) return;
  fb.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  render(e.target.dataset.c);
}});
function render(filter) {{
  const grid = document.getElementById('bookGrid');
  const list = filter ? books.filter(b => b.colleges.includes(filter)) : books;
  grid.innerHTML = list.map(b => {{
    const cover = b.has_cover ? `<img src="data:image/jpeg;base64,${{b.cover}}" alt="${{b.name}}">` : `<div class="no-cover">暂无封面<br>${{b.name}}</div>`;
    const badges = b.colleges.slice(0,2).map(c => `<span class="badge">${{c}}</span>`).join('');
    return `<div class="card"><div class="cover">${{cover}}</div>
    <div class="info"><div class="title">${{b.name}}</div>
    <div class="meta">${{b.author}} · ${{b.edition}}<br>${{b.publisher}}</div>
    <div class="isbn">ISBN: ${{b.isbn || '待补'}}</div>
    <div style="margin-top:6px;">${{badges}}</div></div></div>`;
  }}).join('');
}}
render('');
</script>
</body>
</html>"""

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"展示页已生成: {OUT}")
print(f"共 {len(book_list)} 本教材，{total_covers} 张封面")
