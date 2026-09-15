import json, urllib.request, sys, time

BASE = "https://99ways.instawp.dev/wp-json/wp/v2"
UA = {"User-Agent": "Mozilla/5.0 (99Ways migration read-only)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def get_headers(url):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.headers

def fetch_all(base, fields=None, embed=False, per_page=100):
    items = []
    page = 1
    while True:
        url = f"{base}&per_page={per_page}&page={page}"
        if embed:
            url += "&_embed=1"
        if fields:
            url += f"&_fields={fields}"
        d = get(url)
        if not isinstance(d, list) or len(d) == 0:
            break
        items += d
        if len(d) < per_page:
            break
        page += 1
        time.sleep(0.1)
    return items

print("Fetching posts (full + embed)...")
posts = fetch_all(f"{BASE}/posts?status=publish", embed=True)
json.dump(posts, open("posts.json","w"), ensure_ascii=False)
print(f"  posts: {len(posts)}")

print("Fetching pages (full + embed)...")
pages = fetch_all(f"{BASE}/pages?status=publish", embed=True)
json.dump(pages, open("pages.json","w"), ensure_ascii=False)
print(f"  pages: {len(pages)}")

print("Fetching categories...")
cats = fetch_all(f"{BASE}/categories", per_page=100)
json.dump(cats, open("categories.json","w"), ensure_ascii=False)
print(f"  categories: {len(cats)}")

print("Fetching tags...")
tags = fetch_all(f"{BASE}/tags", per_page=100)
json.dump(tags, open("tags.json","w"), ensure_ascii=False)
print(f"  tags: {len(tags)}")

print("Fetching media (metadata only)...")
media = fetch_all(f"{BASE}/media", fields="id,date,slug,title,alt_text,caption,description,media_type,mime_type,source_url,media_details")
json.dump(media, open("media.json","w"), ensure_ascii=False)
print(f"  media: {len(media)}")

print("Fetching types...")
json.dump(get(f"{BASE}/types"), open("types.json","w"), ensure_ascii=False)

print("Fetching taxonomies...")
json.dump(get(f"{BASE}/taxonomies"), open("taxonomies.json","w"), ensure_ascii=False)

print("Fetching navigation...")
try:
    nav = get(f"{BASE}/navigation?per_page=100")
    json.dump(nav, open("navigation.json","w"), ensure_ascii=False)
    print(f"  navigation: {len(nav)}")
except Exception as e:
    print(f"  navigation error: {e}")

print("Fetching api root...")
json.dump(get("https://99ways.instawp.dev/wp-json/"), open("api-root.json","w"), ensure_ascii=False)

print("DONE")
