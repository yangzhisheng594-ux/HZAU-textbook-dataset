# -*- coding: utf-8 -*-
"""
HZAU 教材封面批量抓取脚本
用法：  python fetch_covers.py
功能：
  1. 读取 metadata.csv（同目录）
  2. 对每条记录解析 ISBN（已填的直接用，未填的通过当当网按书名+主编检索补全）
  3. 按 ISBN 从当当/OpenLibrary 抓取高清封面，保存到 covers/ISBN_书名.jpg
  4. 把补全后的 ISBN 回写到 metadata.csv
说明：运行需要网络；部分图书当当无货或OpenLibrary无记录时标记为"未找到封面"，不影响其余。
"""
import csv, os, sys, time, io, re
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 仓库根目录
CSV_PATH = os.path.join(BASE, "metadata.csv")
COVERS_DIR = os.path.join(BASE, "covers")
os.makedirs(COVERS_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://www.dangdang.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def sanitize(name):
    return re.sub(r'[\\/:*?"<>|\r\n]', '_', str(name))[:60]

def resolve_isbn_by_title(title, author):
    """通过当当搜索补全 ISBN（返回10或13位ISBN，找不到返回None）"""
    url = "https://search.dangdang.com/"
    params = {"key": title, "act": "input"}
    try:
        r = SESSION.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        html = r.text
        # 当当商品链接可能是 https:// 或 // 开头，统一匹配
        m = re.search(r'href="([^"]*product\.dangdang\.com/\d+\.html)"', html)
        if not m:
            return None
        detail = SESSION.get(_norm(m.group(1)), timeout=20).text
        isbn = re.search(r'[IｉＩ][SｓＳ][BｂＢ][NｎＮ][^0-9]{0,10}(\d{9}[\dXx]|\d{13})', detail, re.I)
        return isbn.group(1) if isbn else None
    except Exception as e:
        print("   [ISBN检索失败]", title, e)
        return None

def _norm(url):
    """补全协议前缀（当当封面统一带 _w_ 尺寸标识，不剥离）"""
    if not url:
        return url
    if url.startswith("//"):
        url = "https:" + url
    return url


def download_cover(isbn, title):
    """按 ISBN 从当当下载高清封面，返回保存路径（带重试）"""
    for attempt in range(3):
        candidates = []
        try:
            r = SESSION.get("https://search.dangdang.com/", params={"key": isbn, "act": "input"}, timeout=25)
            if r.status_code == 200:
                m = re.search(r'href="([^"]*product\.dangdang\.com/\d+\.html)"', r.text)
                if m:
                    detail = SESSION.get(_norm(m.group(1)), timeout=25).text
                    img = re.search(r'<img[^>]+id="largePic"[^>]+src="([^"]+)"', detail)
                    if img:
                        candidates.append(img.group(1))
        except Exception as e:
            print("   [当当封面失败]", e)
        # 备用源：OpenLibrary 国际ISBN库（部分国际书）
        candidates.append("https://covers.openlibrary.org/b/isbn/%s-L.jpg" % isbn)

        for url in candidates:
            try:
                url = _norm(url)
                img = SESSION.get(url, timeout=25)
                ct = img.headers.get("Content-Type", "")
                if (img.status_code == 200 and img.content
                        and (ct.startswith("image") or img.content[:4] == b'\x89PNG'
                             or img.content[:2] == b'\xff\xd8')
                        and len(img.content) > 5000):
                    ext = ".png" if (img.content[:4] == b'\x89PNG' or url.lower().endswith(".png")) else ".jpg"
                    path = os.path.join(COVERS_DIR, f"{isbn}_{sanitize(title)}{ext}")
                    with open(path, "wb") as f:
                        f.write(img.content)
                    return path
            except Exception:
                continue
        if attempt < 2:
            time.sleep(2 + attempt * 2)   # 反爬退避
    return None

def main():
    with io.open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0].keys())
    total = len(rows)
    ok = 0; skip = 0
    print("共 %d 条教材记录，开始抓取封面…" % total)
    for i, row in enumerate(rows, 1):
        title = row["教材名称"].strip()
        author = row.get("主编", "").strip()
        isbn = (row.get("ISBN") or "").strip()
        status = row.get("数据状态", "")
        # 纯公共课/马工程(部分)由脚本补ISBN
        if not isbn and ("待脚本补全" in status or not status):
            got = resolve_isbn_by_title(title, author)
            if got:
                row["ISBN"] = got
                row["数据状态"] = "已由脚本补全ISBN"
        isbn = (row.get("ISBN") or "").strip()
        print(f"[{i}/{total}] {title}  ISBN:{isbn or '无'}")
        if not isbn:
            print("   - 无ISBN，跳过封面")
            skip += 1
            continue
        path = download_cover(isbn, title)
        if path:
            print("   ✓ 封面已存:", os.path.basename(path))
            ok += 1
        else:
            print("   ✗ 未找到封面（可后续手动补）")
        time.sleep(1.0)   # 限速，降低被反爬概率

    # 回写补全后的 ISBN（忽略多余字段，避免脏行崩溃）
    with io.open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
    print("\n完成：成功 %d 张，跳过 %d 条（无ISBN）。封面保存在 covers/ 目录，ISBN已回写 metadata.csv。" % (ok, skip))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("运行出错：", e)
        sys.exit(1)
