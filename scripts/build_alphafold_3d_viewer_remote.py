from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build lightweight 3D viewer that fetches PDB from remote URLs.")
    p.add_argument("--annotated-csv", required=True, help="final_top_candidates_with_sites_annotated.csv path")
    p.add_argument("--alphafold-csv", required=True, help="alphafold_models.csv path")
    p.add_argument("--output-html", required=True, help="Output HTML path")
    p.add_argument("--max-items", type=int, default=60, help="Max rows in viewer")
    return p.parse_args()


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def build_entries(annotated_csv: Path, alphafold_csv: Path, max_items: int) -> list[dict[str, Any]]:
    df = pd.read_csv(annotated_csv)
    af = pd.read_csv(alphafold_csv)
    af_map = {
        str(r.get("uniprot_id", "")).strip(): str(r.get("alphafold_pdb_url", "")).strip()
        for _, r in af.iterrows()
        if str(r.get("uniprot_id", "")).strip()
    }

    df = df[
        (df.get("alphafold_status", "").astype(str) == "ok")
        & (df.get("uniprot_id", "").astype(str).str.len() > 0)
    ].copy()
    if "rank" in df.columns:
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
        df = df.sort_values(["rank", "drug_name"], kind="mergesort")
    df = df.head(max_items)

    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        uid = str(r.get("uniprot_id", "")).strip()
        if not uid:
            continue
        pdb_url = af_map.get(uid, "").strip()
        if not pdb_url:
            pdb_url = f"https://alphafold.ebi.ac.uk/files/AF-{uid}-F1-model_v6.pdb"

        rank = int(float(r.get("rank", 0))) if str(r.get("rank", "")).strip() else 0
        drug = str(r.get("drug_name", "")).strip()
        gene = str(r.get("target_gene_symbol", "")).strip()
        residues = str(r.get("predicted_binding_site_residues", "")).strip()
        site_conf = _to_float(r.get("site_confidence", 0.0))
        plddt = _to_float(r.get("alphafold_mean_plddt", 0.0))
        rows.append(
            {
                "label": f"Rank {rank} | {drug} | {gene} | {uid}",
                "rank": rank,
                "drug_name": drug,
                "target_gene_symbol": gene,
                "uniprot_id": uid,
                "alphafold_mean_plddt": plddt,
                "site_confidence": site_conf,
                "predicted_binding_site_residues": residues,
                "pdb_url": pdb_url,
            }
        )
    return rows


def build_html(entries: list[dict[str, Any]]) -> str:
    payload = json.dumps(entries, ensure_ascii=False)
    template = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AlphaFold 3D Viewer (Remote)</title>
  <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
  <style>
    body {
      margin: 0;
      font-family: "Segoe UI", "Noto Sans KR", Arial, sans-serif;
      background: linear-gradient(135deg, #f3f8ff, #eef7f1);
      color: #1f2937;
    }
    .wrap {
      max-width: 1200px;
      margin: 0 auto;
      padding: 12px;
    }
    .card {
      background: rgba(255,255,255,0.94);
      border: 1px solid #dbe4ee;
      border-radius: 12px;
      box-shadow: 0 8px 26px rgba(25,35,60,0.08);
    }
    .toolbar {
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: 8px;
      padding: 10px;
      margin-bottom: 10px;
    }
    .viewer {
      height: 58vh;
      min-height: 340px;
      border: 1px solid #d6e1ed;
      background: #0b1220;
      border-radius: 12px;
      overflow: hidden;
    }
    .meta {
      margin-top: 10px;
      padding: 10px;
      font-size: 14px;
      line-height: 1.45;
      max-height: 32vh;
      overflow: auto;
    }
    .status {
      margin-top: 8px;
      font-size: 13px;
      color: #374151;
    }
    .k { display: inline-block; min-width: 110px; color: #4b5563; font-weight: 600; }
    select, button {
      border-radius: 10px;
      border: 1px solid #cfd9e7;
      padding: 8px 10px;
      background: #fff;
      font-size: 14px;
    }
    @media (max-width: 900px) {
      .toolbar { grid-template-columns: 1fr; }
      .viewer { height: 52vh; min-height: 300px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card toolbar">
      <select id="entrySelect"></select>
      <select id="styleSelect">
        <option value="cartoon_plddt">Cartoon (pLDDT Color)</option>
        <option value="cartoon_chain">Cartoon (Chain Color)</option>
        <option value="stick">Stick</option>
        <option value="sphere">Sphere</option>
      </select>
      <button id="spinBtn">Spin: Off</button>
    </div>
    <div id="viewer" class="card viewer"></div>
    <div class="card meta" id="meta"></div>
    <div class="status" id="status"></div>
  </div>
  <script>
    const entries = __PAYLOAD__;
    const entrySelect = document.getElementById("entrySelect");
    const styleSelect = document.getElementById("styleSelect");
    const spinBtn = document.getElementById("spinBtn");
    const statusEl = document.getElementById("status");
    const meta = document.getElementById("meta");
    let spinOn = false;

    if (!entries.length) {
      document.getElementById("viewer").innerHTML = '<div style="padding:16px;background:#fff;color:#111">No entry found.</div>';
      throw new Error("No entries");
    }
    for (let i = 0; i < entries.length; i++) {
      const op = document.createElement("option");
      op.value = String(i);
      op.textContent = entries[i].label;
      entrySelect.appendChild(op);
    }

    if (!window.$3Dmol) {
      document.getElementById("viewer").innerHTML = '<div style="padding:16px;background:#fff;color:#111">3Dmol load failed.</div>';
      throw new Error("3Dmol load failed");
    }
    const viewer = $3Dmol.createViewer("viewer", { backgroundColor: "white", antialias: true });

    function applyStyle(mode) {
      viewer.setStyle({}, {});
      if (mode === "cartoon_chain") {
        viewer.setStyle({}, { cartoon: { color: "spectrum" } });
      } else if (mode === "stick") {
        viewer.setStyle({}, { stick: { colorscheme: "Jmol" } });
      } else if (mode === "sphere") {
        viewer.setStyle({}, { sphere: { colorscheme: "Jmol", scale: 0.28 } });
      } else {
        viewer.setStyle({}, { cartoon: { colorscheme: { prop: "b", gradient: "rwb", min: 0, max: 100 } } });
      }
    }

    function parseSiteSelection(txt) {
      const sels = [];
      const t = (txt || "").trim();
      if (!t) return sels;
      for (const token of t.split(";")) {
        const x = token.trim();
        if (!x) continue;
        const parts = x.split(":");
        if (parts.length < 2) continue;
        const rc = parts[1];
        const chain = rc[0];
        const resi = parseInt(rc.slice(1), 10);
        if (!Number.isFinite(resi)) continue;
        sels.push({ chain, resi });
      }
      return sels;
    }

    function highlightSite(txt) {
      const sels = parseSiteSelection(txt);
      for (const sel of sels) {
        viewer.setStyle(sel, { stick: { radius: 0.2, color: "gold" } });
      }
      return sels;
    }

    async function render(index) {
      const e = entries[index];
      statusEl.textContent = "Loading structure...";
      try {
        const resp = await fetch(e.pdb_url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const pdb = await resp.text();
        viewer.clear();
        viewer.addModel(pdb, "pdb");
        applyStyle(styleSelect.value);
        const sels = highlightSite(e.predicted_binding_site_residues);
        if (sels.length > 0) {
          viewer.zoomTo(sels);
        } else {
          viewer.zoomTo();
        }
        viewer.spin(spinOn);
        viewer.render();
        statusEl.textContent = "Loaded";
      } catch (err) {
        statusEl.textContent = "Load failed: " + String(err);
      }

      meta.innerHTML = `
        <div><span class="k">Rank</span> ${e.rank || "-"}</div>
        <div><span class="k">Drug</span> ${e.drug_name || "-"}</div>
        <div><span class="k">Target</span> ${e.target_gene_symbol || "-"}</div>
        <div><span class="k">UniProt</span> ${e.uniprot_id || "-"}</div>
        <div><span class="k">Mean pLDDT</span> ${(e.alphafold_mean_plddt || 0).toFixed(2)}</div>
        <div><span class="k">Site Conf</span> ${(e.site_confidence || 0).toFixed(3)}</div>
        <div><span class="k">PDB URL</span> ${e.pdb_url || "-"}</div>
        <div><span class="k">Site Residues</span> ${(e.predicted_binding_site_residues || "-")}</div>
      `;
    }

    entrySelect.addEventListener("change", () => render(Number(entrySelect.value)));
    styleSelect.addEventListener("change", () => {
      applyStyle(styleSelect.value);
      viewer.render();
    });
    spinBtn.addEventListener("click", () => {
      spinOn = !spinOn;
      viewer.spin(spinOn);
      spinBtn.textContent = `Spin: ${spinOn ? "On" : "Off"}`;
      viewer.render();
    });

    render(0);
  </script>
</body>
</html>
"""
    return template.replace("__PAYLOAD__", payload)


def main() -> None:
    args = parse_args()
    annotated = Path(args.annotated_csv)
    af = Path(args.alphafold_csv)
    out = Path(args.output_html)
    out.parent.mkdir(parents=True, exist_ok=True)

    entries = build_entries(annotated, af, max_items=max(1, args.max_items))
    html = build_html(entries)
    out.write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "annotated_csv": str(annotated),
                "alphafold_csv": str(af),
                "output_html": str(out),
                "n_entries": len(entries),
                "html_size": out.stat().st_size if out.exists() else 0,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
