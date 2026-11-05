#!/usr/bin/env python3
"""Regenerate the auto-maintained blocks of the profile README.

Rewrites the content between these marker pairs in README.md:
  <!-- LANGS:START -->      ... <!-- LANGS:END -->        (the language badge card)
  <!-- REPO-LANGS:START --> ... <!-- REPO-LANGS:END -->   (languages-by-repository table)

Everything else in the README (bio, Projects prose, Accounts) is left untouched.

Reads every repo the token can see (public + private), so new repos appear
automatically. Needs a token in GH_TOKEN with read access to your repos
(metadata is enough for listing + languages). Run from the repo root.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("GH_TOKEN (or GITHUB_TOKEN) not set")

# Repos to leave out of the profile entirely (case-insensitive, by name).
# Add any repo you don't want surfaced on your public profile here.
EXCLUDE = {
    "ios-rat-chain-26.3.1-",
}

# Curated badge markup per language. Anything not here gets a plain slate badge,
# so new languages still render — just without a brand logo/colour.
BADGES = {
    "Python": "![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)",
    "TypeScript": "![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)",
    "JavaScript": "![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)",
    "Go": "![Go](https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white)",
    "Rust": "![Rust](https://img.shields.io/badge/Rust-000000?style=flat-square&logo=rust&logoColor=white)",
    "C++": "![C++](https://img.shields.io/badge/C%2B%2B-00599C?style=flat-square&logo=cplusplus&logoColor=white)",
    "C": "![C](https://img.shields.io/badge/C-A8B9CC?style=flat-square&logo=c&logoColor=black)",
    "C#": "![C#](https://img.shields.io/badge/C%23-512BD4?style=flat-square&logo=csharp&logoColor=white)",
    "Swift": "![Swift](https://img.shields.io/badge/Swift-F05138?style=flat-square&logo=swift&logoColor=white)",
    "Kotlin": "![Kotlin](https://img.shields.io/badge/Kotlin-7F52FF?style=flat-square&logo=kotlin&logoColor=white)",
    "Objective-C": "![Objective-C](https://img.shields.io/badge/Objective--C-438EFF?style=flat-square&logo=apple&logoColor=white)",
    "Ruby": "![Ruby](https://img.shields.io/badge/Ruby-CC342D?style=flat-square&logo=ruby&logoColor=white)",
    "Perl": "![Perl](https://img.shields.io/badge/Perl-39457E?style=flat-square&logo=perl&logoColor=white)",
    "Lua": "![Lua](https://img.shields.io/badge/Lua-2C2D72?style=flat-square&logo=lua&logoColor=white)",
    "R": "![R](https://img.shields.io/badge/R-276DC3?style=flat-square&logo=r&logoColor=white)",
    "Fortran": "![Fortran](https://img.shields.io/badge/Fortran-734F96?style=flat-square&logo=fortran&logoColor=white)",
    "Cython": "![Cython](https://img.shields.io/badge/Cython-FEDF5B?style=flat-square&logo=cython&logoColor=black)",
    "Cuda": "![CUDA](https://img.shields.io/badge/CUDA-76B900?style=flat-square&logo=nvidia&logoColor=white)",
    "Shell": "![Shell](https://img.shields.io/badge/Shell-4EAA25?style=flat-square&logo=gnubash&logoColor=white)",
    "PowerShell": "![PowerShell](https://img.shields.io/badge/PowerShell-5391FE?style=flat-square&logo=powershell&logoColor=white)",
    "Nushell": "![Nushell](https://img.shields.io/badge/Nushell-4E9A06?style=flat-square&logo=nushell&logoColor=white)",
    "Xonsh": "![Xonsh](https://img.shields.io/badge/Xonsh-5C6BC0?style=flat-square)",
    "Batchfile": "![Batchfile](https://img.shields.io/badge/Batchfile-C1F12E?style=flat-square&logo=windowsterminal&logoColor=black)",
    "PLpgSQL": "![PL/pgSQL](https://img.shields.io/badge/PL%2FpgSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)",
    "HTML": "![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)",
    "CSS": "![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)",
    "Jinja": "![Jinja](https://img.shields.io/badge/Jinja-B41717?style=flat-square&logo=jinja&logoColor=white)",
    "Smarty": "![Smarty](https://img.shields.io/badge/Smarty-F0C040?style=flat-square)",
    "XSLT": "![XSLT](https://img.shields.io/badge/XSLT-EB8CEB?style=flat-square)",
    "Jupyter Notebook": "![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=flat-square&logo=jupyter&logoColor=white)",
    "TeX": "![TeX](https://img.shields.io/badge/TeX-3D6117?style=flat-square&logo=latex&logoColor=white)",
    "Roff": "![Roff](https://img.shields.io/badge/Roff-ECDEBE?style=flat-square&logoColor=black)",
    "Makefile": "![Makefile](https://img.shields.io/badge/Makefile-427819?style=flat-square&logo=gnu&logoColor=white)",
    "CMake": "![CMake](https://img.shields.io/badge/CMake-064F8C?style=flat-square&logo=cmake&logoColor=white)",
    "Meson": "![Meson](https://img.shields.io/badge/Meson-007800?style=flat-square&logo=meson&logoColor=white)",
    "Dockerfile": "![Docker](https://img.shields.io/badge/Dockerfile-2496ED?style=flat-square&logo=docker&logoColor=white)",
    "Inno Setup": "![Inno Setup](https://img.shields.io/badge/Inno%20Setup-264478?style=flat-square)",
    "Linker Script": "![Linker Script](https://img.shields.io/badge/Linker%20Script-6E4C13?style=flat-square)",
    "ANTLR": "![ANTLR](https://img.shields.io/badge/ANTLR-9DC3E6?style=flat-square&logoColor=black)",
    "Thrift": "![Thrift](https://img.shields.io/badge/Thrift-D22128?style=flat-square&logo=apache&logoColor=white)",
    "Go Template": "![Go Template](https://img.shields.io/badge/Go%20Template-00ADD8?style=flat-square&logo=go&logoColor=white)",
}


def api(path):
    req = urllib.request.Request(API + path)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-readme-bot")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def plain_badge(lang):
    label = lang.replace("-", "--").replace(" ", "%20")
    label = urllib.parse.quote(label, safe="%")
    return f"![{lang}](https://img.shields.io/badge/{label}-607D8B?style=flat-square)"


def badge(lang):
    return BADGES.get(lang, plain_badge(lang))


def list_repos():
    repos, page = [], 1
    while True:
        batch = api(f"/user/repos?per_page=100&affiliation=owner&sort=updated&page={page}")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def main():
    me = api("/user")["login"]
    repos = [r for r in list_repos()
             if r["name"].lower() != me.lower()
             and r["name"].lower() not in EXCLUDE]

    total = {}          # lang -> total bytes across all repos
    per_repo = []       # (name, private, [langs by bytes desc], description)
    for r in repos:
        langs = api(f"/repos/{r['full_name']}/languages")
        for k, v in langs.items():
            if isinstance(v, int):
                total[k] = total.get(k, 0) + v
        ordered = [k for k, _ in sorted(langs.items(), key=lambda x: -x[1])]
        per_repo.append((r["name"], r["private"], ordered, (r.get("description") or "").strip()))

    # Language card: most-used first.
    ordered_langs = [k for k, _ in sorted(total.items(), key=lambda x: -x[1])]
    card = "\n".join(badge(l) for l in ordered_langs)
    card += f"\n\n<sub>All {len(ordered_langs)} languages detected across every repository, public & private.</sub>"

    # Table: public (linked) first, then private (named, not linked).
    pub = [x for x in per_repo if not x[1]]
    priv = [x for x in per_repo if x[1]]
    rows = ["| Repository | Languages |", "|------------|-----------|"]
    for name, _, langs, _desc in pub:
        cell = ", ".join(langs) if langs else "— *(no code detected)*"
        rows.append(f"| [{name}](https://github.com/{me}/{name}) | {cell} |")
    for name, _, langs, _desc in priv:
        cell = ", ".join(langs) if langs else "— *(no code detected)*"
        rows.append(f"| {name} *(private)* | {cell} |")
    table = "\n".join(rows)

    # Projects: description + top languages. Public linked, private named.
    def project_line(name, private, langs, desc, linked):
        head = f"**[{name}](https://github.com/{me}/{name})**" if linked else f"**{name}**"
        if private:
            head += " *(private)*"
        parts = [head]
        if desc:
            parts.append("— " + desc)
        tops = " · ".join(f"`{l}`" for l in langs[:3])
        if tops:
            parts.append("  \n  " + tops)
        return "- " + " ".join(parts)

    proj = ["**Public**\n"]
    for name, priv_flag, langs, desc in pub:
        proj.append(project_line(name, False, langs, desc, linked=True))
    proj.append("\n**Private** *(not linked)*\n")
    for name, priv_flag, langs, desc in priv:
        proj.append(project_line(name, True, langs, desc, linked=False))
    projects = "\n".join(proj)

    readme = open("README.md", encoding="utf-8").read()

    def replace(text, start, end, body):
        pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
        if not pat.search(text):
            sys.exit(f"markers {start}..{end} not found in README")
        return pat.sub(start + "\n" + body + "\n" + end, text)

    readme = replace(readme, "<!-- LANGS:START -->", "<!-- LANGS:END -->", card)
    readme = replace(readme, "<!-- REPO-LANGS:START -->", "<!-- REPO-LANGS:END -->", table)
    readme = replace(readme, "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->", projects)

    open("README.md", "w", encoding="utf-8").write(readme)
    print(f"Updated: {len(ordered_langs)} languages, {len(per_repo)} repos "
          f"({len(pub)} public, {len(priv)} private)")


if __name__ == "__main__":
    main()
