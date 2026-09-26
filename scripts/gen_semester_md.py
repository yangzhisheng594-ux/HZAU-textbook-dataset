# -*- coding: utf-8 -*-
"""生成 学院→专业(25级)→学期→课程清单 的干净markdown，写入课程按学期整理.md"""
import csv, io, os, re
from collections import defaultdict

ROOT = r"C:\Users\yzs\Desktop\HZAU-教材数据集-GitHub"
rows = list(csv.DictReader(io.open(os.path.join(ROOT,"课程教材总表.csv"), encoding="utf-8-sig")))

def clean_course(name):
    """清洗课程名，去掉PDF解析噪音"""
    if not name: return None
    # 跳过明显噪音
    if any(x in name for x in ["大于等于", "的应用", "通识课程", "选修", "实验", "实习", "实践", "论文", "设计", "研讨", "培训"]):
        return None
    if "*" in name or "/" in name: return None
    if re.search(r"\d{3,}", name): return None  # 含课程代码的噪音行
    # 去掉末尾括号里的噪音（如 "2B级学生修读", "3周", "12周，暑期进行"）
    name = re.sub(r"[（(][^）)]*(级学生|周|暑期|学期进行|大于等于|学分)[^）)]*[）)]", "", name)
    # 去掉开头的数字噪音（如 "3社会主义理论体系概论" → 这是被截断的，跳过）
    if re.match(r"^\d+[^第]", name): return None
    # 纯英文跳过
    if re.match(r"^[A-Za-z\s]+$", name): return None
    # 含大量英文的跳过
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

# 聚合
data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for r in rows:
    college = r.get("学院","").strip()
    major = r.get("专业","").strip()
    sem = norm_sem(r.get("学期","").strip())
    course = clean_course(r.get("课程名称","").strip())
    if not college or not major or not sem or not course: continue
    if course not in data[college][major][sem]:
        data[college][major][sem].append(course)

# 学院排序
college_order = ["动物科学技术学院、动物医学院","水产学院","植物科学技术学院","生命科学技术学院",
    "食品科学技术学院","资源与环境学院","园艺林学学院","工学院","经济管理学院",
    "文法学院","外国语学院","公共管理学院","信息学院","化学学院"]

lines = []
lines.append("# 华中农业大学本科课程按学期整理（2025版培养方案）\n")
lines.append("> 格式：学院 → 专业（25级）→ 第X学期：课程清单。教材详情见 `课程教材总表.csv`。\n")

for college in college_order:
    if college not in data: continue
    lines.append(f"\n## {college}\n")
    for major in sorted(data[college].keys()):
        lines.append(f"\n### {major}（25级）\n")
        sems = sorted(data[college][major].keys(), key=lambda x: int(re.search(r"\d+",x).group()))
        for sem in sems:
            courses = data[college][major][sem]
            lines.append(f"- **{sem}**：{'、'.join(courses)}")
    lines.append("")

out = os.path.join(ROOT, "课程按学期整理.md")
with io.open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"已生成: {out}")
print(f"学院数: {len([c for c in college_order if c in data])}")
total_majors = sum(len(data[c]) for c in college_order if c in data)
print(f"专业数: {total_majors}")
