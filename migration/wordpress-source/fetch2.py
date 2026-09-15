import json, urllib.request, time

BASE = "https://99ways.instawp.dev/wp-json/wp/v2"
UA = {"User-Agent": "Mozilla/5.0 (99Ways migration read-only)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_all(path, extra="", per_page=100):
    items = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        url = f"{path}{sep}per_page={per_page}&page={page}{extra}"
        d = get(url)
        if not isinstance(d, list) or len(d) == 0:
            break
        items += d
        if len(d) < per_page:
            break
        page += 1
        time.sleep(0.1)
    return items

print("categories...")
json.dump(fetch_all(f"{BASE}/categories"), open("categories.json","w"), ensure_ascii=False)
print("tags...")
json.dump(fetch_all(f"{BASE}/tags"), open("tags.json","w"), ensure_ascii=False)
print("media...")
media = fetch_all(f"{BASE}/media", extra="&_fields=id,date,slug,title,alt_text,caption,description,media_type,mime_type,source_url,media_details")
json.dump(media, open("media.json","w"), ensure_ascii=False)
print(f"  media: {len(media)}")
print("types...")
json.dump(get(f"{BASE}/types"), open("types.json","w"), ensure_ascii=False)
print("taxonomies...")
json.dump(get(f"{BASE}/taxonomies"), open("taxonomies.json","w"), ensure_ascii=False)
print("navigation...")
try:
    nav = get(f"{BASE}/navigation?per_page=100")
    json.dump(nav, open("navigation.json","w"), ensure_ascii=False)
    print(f"  navigation: {len(nav)}")
except Exception as e:
    print("  nav err", e)
print("api-root...")
json.dump(get("https://99ways.instawp.dev/wp-json/"), open("api-root.json","w"), ensure_ascii=False)
print("DONE")
