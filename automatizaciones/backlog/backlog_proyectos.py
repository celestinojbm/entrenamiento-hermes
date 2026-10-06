#!/usr/bin/env python3
"""Backlog consolidado por proyecto, construido con datos REALES de GitHub.

Campos por elemento: origen, proyecto, tipo, prioridad, dependencia, criterio de aceptación, ejecutor,
estado de CI y enlace. Escribe en una tabla de n8n (homelab_backlog) y en un fichero local.
Solo lectura sobre los repositorios: no comenta, no etiqueta, no fusiona, no despliega.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "n8n"))
import n8n_api as api  # noqa: E402

TABLA = "homelab_backlog"
REPOS = ["celestinojbm/Fluvia", "celestinojbm/Dona-agent", "celestinojbm/nova-context",
         "celestinojbm/entrenamiento-hermes", "celestinojbm/EvolveOS", "celestinojbm/Donalabs",
         "celestinojbm/skill-factory"]
RAIZ_REPOS = "C:/Users/celes"


def gh(ruta, paginas=2):
    """Lectura autenticada con gh (solo GET). Devuelve (lista, error)."""
    salida = []
    for p in range(1, paginas + 1):
        sep = "&" if "?" in ruta else "?"
        p_ = subprocess.run(["gh", "api", f"{ruta}{sep}per_page=100&page={p}"], capture_output=True, text=True, timeout=60)
        if p_.returncode != 0:
            return salida, (p_.stderr or "").strip()[:200]
        try:
            d = json.loads(p_.stdout)
        except Exception as e:  # noqa: BLE001
            return salida, f"json inválido: {str(e)[:80]}"
        if isinstance(d, dict):
            d = d.get("check_runs") or d.get("workflow_runs") or d.get("items") or []
        if not isinstance(d, list) or not d:
            break
        salida.extend(d)
    return salida, None


def correspondencia():
    """Verifica la correspondencia proyecto↔repositorio leyendo la descripción real del repo."""
    mapa = {}
    for repo in REPOS:
        p = subprocess.run(["gh", "api", f"repos/{repo}", "--jq", "{name,description,private,default_branch}"],
                           capture_output=True, text=True, timeout=40)
        if p.returncode != 0:
            mapa[repo] = {"proyecto": repo.split("/")[1], "descripcion": "(sin acceso)", "confirmada": False}
            continue
        d = json.loads(p.stdout)
        desc = (d.get("description") or "").strip()
        mapa[repo] = {"proyecto": repo.split("/")[1], "descripcion": desc[:90],
                      "rama": d.get("default_branch"), "confirmada": True}
    return mapa


def prioridad(pr, checks_ok, checks_fallo, etiquetas):
    p = 50
    if etiquetas:
        et = " ".join(etiquetas).lower()
        if any(k in et for k in ("bug", "crítico", "critical", "seguridad")):
            p += 30
        if "dependencies" in et or "javascript" in et:
            p -= 10
    if checks_fallo:
        p += 20
    elif not checks_ok:
        p += 5
    if pr.get("draft") is False:
        p += 10
    antig = (datetime.now(timezone.utc) - datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))).days
    p += min(antig // 7, 10)
    return max(0, min(100, p))


def criterio(pr, checks_ok):
    partes = ["CI en verde" if checks_ok else "CI pendiente o en fallo"]
    partes.append("PR fuera de borrador" if pr.get("draft") else "PR en borrador")
    partes.append("sin conflictos" if pr.get("mergeable") else "resolver conflictos")
    return " · ".join(partes)


def ejecutor(pr, repo):
    rama = (pr.get("head") or {}).get("ref") or ""
    if rama.startswith("claude/") or "claude" in (pr.get("user") or {}).get("login", ""):
        return "claude-code (no intervenir)"
    if os.path.isdir(os.path.join(RAIZ_REPOS, repo.split("/")[1].replace("-agent", ""))):
        return "ejecutor-local-msi"
    return "n8n (solo lectura)"


def main() -> int:
    print("=== CORRESPONDENCIA PROYECTO↔REPOSITORIO (verificada en GitHub) ===")
    mapa = correspondencia()
    for repo, d in mapa.items():
        print(f"  {repo:38} rama={d.get('rama') or '?':22} desc='{(d.get('descripcion') or '')[:60]}'")

    filas = []
    for repo, meta in mapa.items():
        proyecto = repo.split("/")[1]
        prs, err = gh(f"repos/{repo}/pulls?state=open")
        if err:
            print(f"  {repo}: PRs no legibles ({err[:80]})")
            continue
        issues, err2 = gh(f"repos/{repo}/issues?state=open")
        issues = [i for i in (issues or []) if not i.get("pull_request")]
        print(f"\n  --- {proyecto}: {len(prs)} PR abiertos · {len(issues)} issues abiertos")
        for pr in prs:
            try:
                checks, _ = gh(f"repos/{repo}/commits/{(pr.get('head') or {}).get('sha')}/check-runs")
                ok = [c for c in (checks or []) if c.get("conclusion") == "success"]
                mal = [c for c in (checks or []) if c.get("conclusion") in ("failure", "timed_out", "cancelled")]
            except Exception:  # noqa: BLE001
                ok, mal = [], []
            etiquetas = [l.get("name") for l in (pr.get("labels") or [])]
            cuerpo = (pr.get("body") or "")
            dep = ""
            m = re.search(r"(?i)(depends? on|depende de|bloquead[oa] por|blocked by)\s*#?(\d+)", cuerpo)
            if m:
                dep = f"#{m.group(2)}"
            elif (pr.get("head") or {}).get("ref", "").count("/") and "dependabot" in (pr.get("head") or {}).get("ref", ""):
                dep = "grupo dependabot"
            filas.append({
                "clave": f"{repo}#{pr['number']}@{pr['head']['sha'][:8]}",
                "proyecto": proyecto, "repo": repo, "tipo": "pull_request", "numero": pr["number"],
                "titulo": (pr.get("title") or "")[:120], "origen": "GitHub PR abierto",
                "estado": "abierto", "borrador": bool(pr.get("draft")),
                "prioridad": prioridad(pr, len(ok) > 0, len(mal) > 0, etiquetas),
                "ci": ("fallo" if mal else ("en_curso" if not ok else "verde")),
                "dependencia": dep, "criterio": criterio(pr, len(ok) > 0 and not mal),
                "ejecutor": ejecutor(pr, repo), "url": pr.get("html_url"),
                "actualizado": pr.get("updated_at"), "etiquetas": ",".join(etiquetas)[:60],
            })
        for i in issues:
            etiquetas = [l.get("name") for l in (i.get("labels") or [])]
            filas.append({
                "clave": f"{repo}#i{i['number']}", "proyecto": proyecto, "repo": repo, "tipo": "issue",
                "numero": i["number"], "titulo": (i.get("title") or "")[:120], "origen": "GitHub issue abierto",
                "estado": "abierto", "borrador": False,
                "prioridad": 55 + (20 if any("bug" in (e or "").lower() for e in etiquetas) else 0),
                "ci": "n/a", "dependencia": "", "criterio": "cerrable con evidencia enlazada en el issue",
                "ejecutor": "ejecutor-local-msi", "url": i.get("html_url"),
                "actualizado": i.get("updated_at"), "etiquetas": ",".join(etiquetas)[:60],
            })

    print(f"\n=== BACKLOG: {len(filas)} elementos ===")
    por_proyecto = {}
    for f in filas:
        por_proyecto.setdefault(f["proyecto"], []).append(f)
    for proy, fs in sorted(por_proyecto.items(), key=lambda x: -len(x[1])):
        alto = [x for x in fs if x["prioridad"] >= 70]
        print(f"  {proy:22} {len(fs):3} elementos · {len(alto):2} de prioridad alta · "
              f"CI en fallo: {len([x for x in fs if x['ci'] == 'fallo'])}")
        for x in sorted(fs, key=lambda y: -y["prioridad"])[:3]:
            print(f"     [{x['prioridad']:3}] {x['tipo']} #{x['numero']} ci={x['ci']} ejecutor={x['ejecutor']} — {x['titulo'][:62]}")

    # tabla en n8n
    t = next((x for x in (api.get("/api/v1/data-tables?limit=50").get("data") or []) if x.get("name") == TABLA), None)
    COLS = [("clave", "string"), ("proyecto", "string"), ("repo", "string"), ("tipo", "string"), ("numero", "number"),
            ("titulo", "string"), ("origen", "string"), ("estado", "string"), ("prioridad", "number"), ("ci", "string"),
            ("dependencia", "string"), ("criterio", "string"), ("ejecutor", "string"), ("url", "string"),
            ("actualizado", "string"), ("borrador", "boolean"), ("etiquetas", "string")]
    if not t:
        t = api.post("/api/v1/data-tables", {"name": TABLA, "columns": [{"name": n, "type": y} for n, y in COLS]})
        print(f"  tabla creada: {TABLA} ({t.get('id')})")
    else:
        existentes = {c.get("name") for c in (lambda r: r if isinstance(r, list) else (r.get("data") or []))(
            api.get(f"/api/v1/data-tables/{t['id']}/columns"))}
        for n, y in COLS:
            if n not in existentes:
                try:
                    api.post(f"/api/v1/data-tables/{t['id']}/columns", {"name": n, "type": y})
                    print(f"  columna añadida: {n}")
                except Exception as e:  # noqa: BLE001
                    print(f"  columna {n}: {str(e)[:110]}")
    r = api.post(f"/api/v1/data-tables/{t['id']}/rows", {"data": filas})
    print(f"  escrito en n8n: {json.dumps(r)}")
    ruta_local = os.path.join(AQUI, "backlog_proyectos.json")
    json.dump({"generado": datetime.now(timezone.utc).isoformat(), "elementos": filas},
              open(ruta_local, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  fichero local: {ruta_local}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
