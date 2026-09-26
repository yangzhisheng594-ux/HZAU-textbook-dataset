# -*- coding: utf-8 -*-
"""生成 学院→专业(25级)→学期→课程+教材封面 的markdown，封面内嵌"""
import csv, io, os, re
from collections import defaultdict

ROOT = r"C:\Users\yzs\Desktop\HZAU-教材数据集-GitHub"
COVERS_DIR = os.path.join(ROOT, "covers")

# 1. 建立 ISBN -> 封面文件名 映射
isbn_to_cover = {}
if os.path.isdir(COVERS_DIR):
    for fn in os.listdir(COVERS_DIR):
        if fn.endswith(".jpg") or fn.endswith(".png"):
            m = re.match(r"(\d{10,13}[\dXx]?)_", fn)
            if m:
                isbn_to_cover[m.group(1)] = fn

# 2. 建立 课程名 -> (教材名, ISBN, 封面文件) 映射（取第一条有教材的）
course_to_book = {}
rows = list(csv.DictReader(io.open(os.path.join(ROOT,"课程教材总表.csv"), encoding="utf-8-sig")))
for r in rows:
    course = r.get("课程名称","").strip()
    book = r.get("教材名称","").strip()
    isbn = r.get("ISBN","").strip()
    if not course or not book: continue
    if course not in course_to_book:
        cover = isbn_to_cover.get(isbn, "")
        course_to_book[course] = (book, isbn, cover)

def clean_course(name):
    if not name: return None
    if any(x in name for x in ["大于等于", "的应用", "通识课程", "选修", "实验", "实习", "实践", "论文", "设计", "研讨", "培训"]):
        return None
    if "*" in name or "/" in name: return None
    if re.search(r"\d{3,}", name): return None
    name = re.sub(r"[（(][^）)]*(级学生|周|暑期|学期进行|大于等于|学分)[^）)]*[）)]", "", name)
    if re.match(r"^\d+[^第]", name): return None
    if re.match(r"^[A-Za-z\s]+$", name): return None
    if len(re.findall(r"[A-Za-z]", name)) > len(name) * 0.5: return None
    name = name.strip()
    if len(name) < 2: return None
    return name

def norm_sem(sem):
    if not sem: return None
    m = re.search(r"(\d+)", sem)
    if not m: return None
    n = int(m.group(1))
    if n < 1 or n > 8: return None
    return f"第{n}学期"

# 3. 聚合
data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for r in rows:
    college = r.get("学院","").strip()
    major = r.get("专业","").strip()
    sem = norm_sem(r.get("学期","").strip())
    course = clean_course(r.get("课程名称","").strip())
    if not college or not major or not sem or not course: continue
    if course not in data[college][major][sem]:
        data[college][major][sem].append(course)

college_order = ["动物科学技术学院、动物医学院","水产学院","植物科学技术学院","生命科学技术学院",
    "食品科学技术学院","资源与环境学院","园艺林学学院","工学院","经济管理学院",
    "文法学院","外国语学院","公共管理学院","信息学院","化学学院"]

lines = []
lines.append("# 华中农业大学本科课程按学期整理（2025版培养方案）\n")
lines.append("> 格式：学院 → 专业（25级）→ 第X学期：课程 + 教材封面。封面图来自 `covers/` 目录。\n")

img_count = 0
for college in college_order:
    if college not in data: continue
    lines.append(f"\n## {college}\n")
    for major in sorted(data[college].keys()):
        lines.append(f"\n### {major}（25级）\n")
        sems = sorted(data[college][major].keys(), key=lambda x: int(re.search(r"\d+",x).group()))
        for sem in sems:
            lines.append(f"\n**{sem}**\n")
            for course in data[college][major][sem]:
                book_info = course_to_book.get(course)
                if book_info:
                    book, isbn, cover = book_info
                    if cover:
                        img_count += 1
                        cover_path = f"covers/{cover}"
                        lines.append(f"- **{course}** — 《{book}》（ISBN: {isbn}）")
                        lines.append(f"  ![{book}]({cover_path})")
                    else:
                        lines.append(f"- **{course}** — 《{book}》（ISBN: {isbn}，封面待补）")
                else:
                    lines.append(f"- {course}")
        lines.append("")

out = os.path.join(ROOT, "课程按学期整理.md")
with io.open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"已生成: {out}")
print(f"内嵌封面数: {img_count}")
print(f"学院数: {len([c for c in college_order if c in data])}")
total_majors = sum(len(data[c]) for c in college_order if c in data)
print(f"专业数: {total_majors}")
