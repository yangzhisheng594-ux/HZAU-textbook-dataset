# -*- coding: utf-8 -*-
"""
解析华农2025版培养方案PDF文本，提取每个专业每学期课程总表。
输入: _pdf文本/*.txt
输出: ../课程总表.csv  列: 学院,专业,学期,课程代码,课程名称,学分,备注
"""
import os, re, glob, csv, io

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TXT_DIR = os.path.join(ROOT, "_pdf文本")
OUT = os.path.join(ROOT, "课程总表.csv")

SEM_CN = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
def sem_num(s):
    s = s.strip()
    if s.isdigit(): return int(s)
    if s in SEM_CN: return SEM_CN[s]
    # 十一 etc
    if "十一" in s: return 11
    return None

COLLEGE_MAP = {
 "1植物科学技术学院":"植物科学技术学院",
 "2动物科学技术学院、动物医学院":"动物科学技术学院、动物医学院",
 "3资源与环境学院":"资源与环境学院",
 "4生命科学技术学院":"生命科学技术学院",
 "5园艺林学学院":"园艺林学学院",
 "6经济管理学院":"经济管理学院",
 "7工学院":"工学院",
 "8水产学院":"水产学院",
 "9食品科学技术学院":"食品科学技术学院",
 "10化学学院":"化学学院",
 "11文法学院":"文法学院",
 "12外国语学院":"外国语学院",
 "13公共管理学院":"公共管理学院",
 "14信息学院":"信息学院",
 "张之洞班":"张之洞班(拔尖)",
}
def college_of(fn):
    base = os.path.splitext(os.path.basename(fn))[0]
    base = re.sub(r"\(1\)$","",base)
    for k,v in COLLEGE_MAP.items():
        if base.startswith(k): return v
    return base

CODE_RE = re.compile(r"\d{9,13}")
rows = []
for txt in sorted(glob.glob(os.path.join(TXT_DIR, "*.txt"))):
    college = college_of(txt)
    major = None; sem = None
    for raw in open(txt, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("===") or re.match(r"^-\s*\d+\s*-$", line):
            continue
        m_major = re.match(r"^(.{2,20}?)专业指导性修读计划\s*$", line)
        if m_major:
            major = m_major.group(1).strip()
            continue
        m_sem = re.search(r"(秋季|春季)学期（第(.+?)学期）", line)
        if m_sem:
            sem = sem_num(m_sem.group(2))
            continue
        if major is None or sem is None:
            continue
        # 跳过表头/小计/学年行
        if "课程代码" in line and "课程名称" in line: continue
        if line.startswith("小计") or line.startswith("合计"): continue
        if re.match(r"^第[一二三四五六七八九十]+学年$", line): continue
        # 必须含 9-13 位课程代码才算具体课程
        cm = CODE_RE.search(line)
        if not cm:
            # 无代码的类别行（外语类/体育类/通识课程）
            if re.match(r"^(外语类|体育类|通识课程|思政类|心理健康)", line):
                note = "选修类别" if "通识" in line else "必修类别"
                rows.append([college, major, sem, "", line.split()[0], "", note])
            continue
        code = cm.group(0)
        rest = line.replace(code, " ", 1)
        # 学分取末尾的数字
        nums = re.findall(r"\d+(?:\.\d+)?", rest)
        credit = nums[-1] if nums else ""
        name = re.sub(r"[\d\.\s]+$", "", rest).strip()
        name = re.sub(r"\s+", "", name)
        if not name: continue
        note = "选修" if "选修" in line else "必修"
        rows.append([college, major, f"第{sem}学期", code, name, credit, note])

with io.open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["学院","专业","学期","课程代码","课程名称","学分","备注"])
    w.writerows(rows)
print("解析完成，课程条目:", len(rows))
print("覆盖专业数:", len(set(r[1] for r in rows if r[1])))
# 打印各专业课程数预览
from collections import Counter
c = Counter(r[1] for r in rows if r[1])
for k,v in c.items(): print(f"  {k}: {v}门")
