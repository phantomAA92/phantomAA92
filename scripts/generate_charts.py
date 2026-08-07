
#!/usr/bin/env python3
import os, requests, json
from collections import defaultdict
USER = os.getenv("GITHUB_OWNER") or "phantomAA92"
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
OUT_DIR = os.path.join("assets", "github-charts")
LANG_DONUT = os.path.join(OUT_DIR, "languages-donut.png")
REPOS_PIE = os.path.join(OUT_DIR, "top-repos-pie.png")
QC_URL = "https://quickchart.io/chart"
os.makedirs(OUT_DIR, exist_ok=True)
def paginate(url, params=None):
    params = params or {"per_page":100,"page":1}
    results=[]
    while url:
        resp=requests.get(url, headers=HEADERS, params=params); resp.raise_for_status()
        results.extend(resp.json())
        link=resp.headers.get("Link",""); next_url=None
        if link:
            for p in link.split(","):
                if 'rel=\"next\"' in p:
                    next_url=p[p.find("<")+1:p.find(">")]; break
        if not next_url: break
        url=next_url; params=None
    return results
def list_repos_for_user(username):
    url=f"https://api.github.com/users/{username}/repos"
    repos=paginate(url, params={"per_page":100,"type":"owner"})
    if TOKEN:
        try:
            me=requests.get("https://api.github.com/user", headers=HEADERS); me.raise_for_status()
            if me.json().get("login","").lower()==username.lower():
                more=paginate("https://api.github.com/user/repos", params={"per_page":100,"affiliation":"owner"})
                repos_map={r["full_name"]:r for r in repos}
                for r in more:
                    if r.get("owner",{}).get("login","").lower()==username.lower():
                        repos_map[r["full_name"]]=r
                repos=list(repos_map.values())
        except requests.HTTPError:
            pass
    return repos
def get_repo_languages(full_name):
    resp=requests.get(f"https://api.github.com/repos/{full_name}/languages", headers=HEADERS); resp.raise_for_status(); return resp.json()
def aggregate_languages(repos):
    total=defaultdict(int); repo_lang_bytes={}
    for r in repos:
        full=r["full_name"]
        try: langs=get_repo_languages(full)
        except requests.HTTPError: langs={}
        repo_lang_bytes[full]=sum(langs.values())
        for lang,b in langs.items(): total[lang]+=b
    return dict(total), repo_lang_bytes
def top_n(d,n=8): return dict(sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n])
def hex_colors(n):
    palette=["#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F","#EDC948","#B07AA1","#FF9DA7","#9C755F","#BAB0AC"]
    return [palette[i%len(palette)] for i in range(n)]
def build_chart_and_save(cfg,out_path,width=600,height=400,bg="transparent"):
    params={"c":json.dumps(cfg),"w":width,"h":height,"bkg":bg,"format":"png"}
    resp=requests.get(QC_URL, params=params); resp.raise_for_status()
    with open(out_path,"wb") as f: f.write(resp.content)
    print("Saved", out_path)
def main():
    print("Listing repos for", USER)
    repos=list_repos_for_user(USER); print("Found", len(repos), "repos")
    langs_total, repo_bytes = aggregate_languages(repos)
    if not langs_total: print("No language data. Exiting."); return
    top_langs=top_n(langs_total,8); others=sum(langs_total.values())-sum(top_langs.values())
    labels=list(top_langs.keys()); data=list(top_langs.values())
    if others>0: labels.append("Other"); data.append(others)
    colors=hex_colors(len(labels))
    donut_cfg={"type":"doughnut","data":{"labels":labels,"datasets":[{"data":data,"backgroundColor":colors,"borderColor":"#fff","borderWidth":2}]},"options":{"plugins":{"legend":{"position":"right","labels":{"usePointStyle":True}},"title":{"display":True,"text":f"Languages for {USER}"}},"maintainAspectRatio":False}}
    top_repos=top_n(repo_bytes,8); repo_labels=list(top_repos.keys()); repo_data=list(top_repos.values()); repo_colors=hex_colors(len(repo_labels))
    pie_cfg={"type":"pie","data":{"labels":repo_labels,"datasets":[{"data":repo_data,"backgroundColor":repo_colors,"borderColor":"#fff","borderWidth":2}]},"options":{"plugins":{"legend":{"position":"right","labels":{"usePointStyle":True}},"title":{"display":True,"text":f"Top repos by language bytes ({USER})"}},"maintainAspectRatio":False}}
    build_chart_and_save(donut_cfg, LANG_DONUT); build_chart_and_save(pie_cfg, REPOS_PIE)
if __name__=="__main__": main()
