# gallery_deluxe.py
import csv
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from flask import Flask, render_template_string, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "any_secret_key"

MEMBERS = [
    {"name": "上村ひなの", "ct": 21, "csv": "hinano_blog_list.csv", "color": "#ff9db6"},
    {"name": "正源司陽子", "ct": 29, "csv": "shogenji_blog_list.csv", "color": "#8fc8ff"},
    {"name": "藤嶌果歩", "ct": 33, "csv": "fujishima_blog_list.csv", "color": "#ffd38f"},
]
BASE_URL = "https://www.hinatazaka46.com"
THUMBNAIL_FALLBACK = "https://placehold.co/300x300?text=No+Image"

def parse_date_tuple(date_str):
    try:
        ds = date_str.strip()
        parts = ds.replace(".", " ").replace(":", " ").split()
        parts = [int(p) for p in parts]
        while len(parts) < 5:
            parts.append(0)
        return tuple(parts[:5])
    except:
        return (0,0,0,0,0)

def load_csv(path, member_name, color):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["メンバー"] = member_name
            r.setdefault("サムネイル", "")
            r.setdefault("抜粋", "")
            r["color"] = color
            items.append(r)
    return items

def load_all_articles():
    all_items = []
    for m in MEMBERS:
        all_items += load_csv(m["csv"], m["name"], m["color"])
    all_items.sort(key=lambda x: parse_date_tuple(x.get("日付", "")), reverse=True)
    return all_items

def fetch_member_to_csv(ct_id, csv_path, max_pages=1, sleep_seconds=0.3):
    rows = []
    page = 0
    count = 0
    while True:
        if max_pages and page >= max_pages:
            break
        list_url = f"{BASE_URL}/s/official/diary/member/list?ct={ct_id}&page={page}"
        res = requests.get(list_url)
        if res.status_code != 200:
            break
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.select("a.c-button-blog-detail")
        if not links:
            break
        for a in links:
            article_url = urljoin(BASE_URL, a.get("href"))
            art_res = requests.get(article_url)
            if art_res.status_code != 200:
                continue
            art_soup = BeautifulSoup(art_res.text, "html.parser")
            title_tag = art_soup.find("div", class_="c-blog-article__title")
            date_tag = art_soup.find("div", class_="c-blog-article__date")
            body_tag = art_soup.find("div", class_="c-blog-article__text")
            title = title_tag.get_text(strip=True) if title_tag else ""
            date = date_tag.get_text(strip=True) if date_tag else ""
            excerpt = ""
            if body_tag:
                txt = body_tag.get_text("\n", strip=True)
                excerpt = txt.strip().replace("\n", " ")
                if len(excerpt) > 180:
                    excerpt = excerpt[:177].rsplit(" ", 1)[0] + "…"
            thumb = ""
            if body_tag:
                img = body_tag.find("img")
                if img and img.get("src"):
                    thumb = urljoin(article_url, img.get("src"))
            rows.append([date, title, article_url, thumb, excerpt])
            count += 1
            if count >= 10:
                break
            time.sleep(sleep_seconds)
        page += 1
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["日付", "タイトル", "URL", "サムネイル", "抜粋"])
        writer.writerows(rows)
    return count

def update_all_members():
    result = {}
    for m in MEMBERS:
        try:
            cnt = fetch_member_to_csv(m["ct"], m["csv"], max_pages=1)
            result[m["name"]] = {"ok": True, "count": cnt}
        except Exception as e:
            result[m["name"]] = {"ok": False, "error": str(e)}
    return result

TEMPLATE = """<!doctype html><html lang="ja"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>日向坂46 ブログギャラリー Deluxe</title>
<style>
body{font-family:system-ui,Arial;margin:0;padding:18px;background:#f6f8fb}
.header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.btn{padding:8px 10px;border-radius:8px;border:0;background:#fff;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.08)}
.btn.primary{background:linear-gradient(90deg,#ff66a3,#ff9db6);color:#fff;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-top:14px}
.card{background:#fff;border-radius:12px;padding:12px;box-shadow:0 4px 12px rgba(0,0,0,0.08);text-align:center}
.thumb{width:140px;height:140px;border-radius:50%;object-fit:cover}
</style></head><body>
<div class="header">
<h2>日向坂46 ブログギャラリー Deluxe</h2>
<form method="post" action="/update"><button class="btn primary">🔄 最新を取得</button></form>
</div>
<div>記事数: {{articles|length}}</div>
<div class="grid">
{% for a in articles %}
<div class="card">
<img src="{{a['サムネイル'] or fallback}}" class="thumb">
<div><a href="{{a['URL']}}" target="_blank">{{a['タイトル']}}</a></div>
<div>{{a['日付']}}・{{a['メンバー']}}</div>
</div>
{% endfor %}
</div></body></html>"""

@app.route("/", methods=["GET"])
def index():
    articles = load_all_articles()
    return render_template_string(TEMPLATE, articles=articles, fallback=THUMBNAIL_FALLBACK)

@app.route("/update", methods=["POST"])
def update():
    update_all_members()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
