# -*- coding: utf-8 -*-
"""
对 课程教材总表.csv 批量补 ISBN + 下载高清封面（v3 豆瓣稳定版）。
运行：
    pip install requests
    python scripts\fetch_master.py
结果：
  - covers\ISBN_书名.jpg  高清封面（豆瓣大图）
  - ISBN 列自动回填到 课程教材总表.csv
"""
import csv, os, io, re, time, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "课程教材总表.csv")
COVERS = os.path.join(ROOT, "covers")
os.makedirs(COVERS, exist_ok=True)

H = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
     "Referer":"https://book.douban.com/","Accept-Language":"zh-CN,zh;q=0.9"}
s = requests.Session(); s.headers.update(H)

def clean_title(book):
    """去掉括号版次、空格，得到干净搜索词"""
    t = re.sub(r"（.*?）|\(.*?\)", "", book)
    t = re.sub(r"\s+", "", t)
    return t.strip()

def douban_search(query):
    """豆瓣搜索建议接口，返回最佳匹配的 {title,url,pic,year,author}，失败返回None"""
    for attempt in range(2):
        try:
            r = s.get("https://book.douban.com/j/subject_suggest", params={"q":query}, timeout=15)
            if r.status_code==200 and r.text.strip():
                data = r.json()
                if data:
                    # 选标题最匹配的（优先完全包含搜索词）
                    best = None
                    for it in data:
                        title = it.get("title","")
                        if query in title or title in query:
                            best = it; break
                    return best or data[0]
        except Exception:
            pass
        time.sleep(1.5)
    return None

def douban_isbn(subject_url):
    """从豆瓣图书详情页提取ISBN"""
    try:
        d = s.get(subject_url, timeout=15).text
        m = re.search(r'ISBN[:：\s]*</span>\s*([\dXx-]+)', d)
        if m: return m.group(1).replace("-","")
        m = re.search(r'97[89]\d{10}', d)
        if m: return m.group(0)
    except Exception:
        pass
    return None

def download_cover(pic_url, isbn, book):
    """下载豆瓣大图（把 /s/ 换成 /l/），保存到 covers/"""
    large = pic_url.replace("/s/public/","/l/public/")
    try:
        img = s.get(large, timeout=20)
        if img.status_code==200 and len(img.content)>5000:
            safe = re.sub(r'[\\/:*?"<>|]',"_",book)[:50]
            ext = ".png" if img.content[:4]==b"\x89PNG" else ".jpg"
            path = os.path.join(COVERS, f"{isbn}_{safe}{ext}")
            open(path,"wb").write(img.content)
            return True
    except Exception:
        pass
    return False

# 读取CSV，按书名去重
rows = list(csv.DictReader(io.open(CSV, encoding="utf-8-sig")))
fields = list(rows[0].keys())
unique = {}
for r in rows:
    b = (r.get("教材名称") or "").strip()
    if b and b not in unique:
        unique[b] = {"isbn": (r.get("ISBN") or "").strip()}

print(f"共 {len(rows)} 行，去重后 {len(unique)} 本教材待处理\n")
ok = 0
for idx, (book, info) in enumerate(unique.items(), 1):
    try:
        query = clean_title(book)
        if not query:
            continue
        res = douban_search(query)
        if not res:
            print(f"[{idx}/{len(unique)}] {book}: 豆瓣无结果"); time.sleep(1.2); continue
        isbn = info["isbn"] or douban_isbn(res["url"])
        if isbn: info["isbn"] = isbn
        got_cover = False
        if isbn and res.get("pic"):
            got_cover = download_cover(res["pic"], isbn, book)
        if got_cover: ok += 1
        print(f"[{idx}/{len(unique)}] {book} -> ISBN {isbn or '?'} {'+封面' if got_cover else ''}")
    except Exception as e:
        print(f"[{idx}] {book}: 出错 {e}")
    time.sleep(1.2)

# 回填ISBN
for r in rows:
    b = (r.get("教材名称") or "").strip()
    if b in unique and unique[b]["isbn"] and not (r.get("ISBN") or "").strip():
        r["ISBN"] = unique[b]["isbn"]

with io.open(CSV, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader(); w.writerows(rows)

print(f"\n完成：{ok} 张高清封面已下载到 covers\\，ISBN 已回填到 课程教材总表.csv")
