from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build a local interactive 3D HTML viewer for AlphaFold structures from final_top_candidates_with_sites.csv"
    )
    p.add_argument("--input-csv", required=True, help="Path to final_top_candidates_with_sites.csv")
    p.add_argument("--pocket-csv", default="", help="Optional pocket CSV with columns: uniprot_id,predicted_binding_site_residues,heuristic_site_confidence")
    p.add_argument("--output-html", required=True, help="Output HTML path")
    p.add_argument("--max-items", type=int, default=60, help="Max rows to include in viewer data")
    p.add_argument("--dedupe-uniprot", action="store_true", help="Keep only one entry per UniProt to reduce HTML size")
    p.add_argument(
        "--backbone-threshold-atoms",
        type=int,
        default=12000,
        help="If ATOM count exceeds this threshold, keep only backbone atoms (N,CA,C,O)",
    )
    return p.parse_args()


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _compact_pdb_for_viewer(pdb_text: str, backbone_threshold_atoms: int = 12000) -> tuple[str, str, int, int]:
    atom_total = 0
    for line in pdb_text.splitlines():
        if line.startswith("ATOM  "):
            atom_total += 1
    use_backbone_only = atom_total > max(0, backbone_threshold_atoms)
    atom_kept = 0
    keep_prefixes = ("ATOM  ", "HETATM", "TER", "MODEL ", "ENDMDL", "END")
    out_lines: list[str] = []
    for line in pdb_text.splitlines():
        if line.startswith("ATOM  "):
            if use_backbone_only:
                atom_name = line[12:16].strip()
                if atom_name not in {"N", "CA", "C", "O"}:
                    continue
            out_lines.append(line)
            atom_kept += 1
            continue
        if line.startswith("HETATM"):
            if not use_backbone_only:
                out_lines.append(line)
            continue
        if line.startswith(keep_prefixes):
            out_lines.append(line)
    if out_lines and out_lines[-1] != "END":
        out_lines.append("END")
    mode = "backbone_only" if use_backbone_only else "full_atoms"
    return "\n".join(out_lines) + ("\n" if out_lines else ""), mode, atom_total, atom_kept


def load_entries(
    input_csv: Path,
    pocket_csv: Path | None,
    max_items: int,
    dedupe_uniprot: bool = False,
    backbone_threshold_atoms: int = 12000,
) -> list[dict[str, Any]]:
    df = pd.read_csv(input_csv)
    pocket_map: dict[str, dict[str, Any]] = {}
    if pocket_csv is not None and pocket_csv.exists():
        dfp = pd.read_csv(pocket_csv)
        if "uniprot_id" in dfp.columns:
            for _, pr in dfp.iterrows():
                uid = str(pr.get("uniprot_id", "")).strip()
                if not uid:
                    continue
                pocket_map[uid] = {
                    "predicted_binding_site_residues": str(pr.get("predicted_binding_site_residues", "")).strip(),
                    "heuristic_site_confidence": _to_float(pr.get("heuristic_site_confidence", 0.0), 0.0),
                    "heuristic_status": str(pr.get("heuristic_status", "")).strip(),
                }

    keep = df[
        (df.get("alphafold_status", "").astype(str) == "ok")
        & (df.get("alphafold_pdb_path", "").astype(str).str.len() > 0)
    ].copy()
    keep = keep.head(max_items)

    entries: list[dict[str, Any]] = []
    seen_uid: set[str] = set()
    for i, row in keep.iterrows():
        pdb_path = Path(str(row.get("alphafold_pdb_path", "")).strip())
        if not pdb_path.exists():
            continue
        pdb_text_raw = pdb_path.read_text(encoding="utf-8", errors="ignore")
        pdb_text, compact_mode, atom_total, atom_kept = _compact_pdb_for_viewer(
            pdb_text_raw, backbone_threshold_atoms=backbone_threshold_atoms
        )
        rank = _to_int(row.get("rank", 0), 0)
        drug = str(row.get("drug_name", "")).strip()
        gene = str(row.get("target_gene_symbol", "")).strip()
        uid = str(row.get("uniprot_id", "")).strip()
        if dedupe_uniprot and uid:
            if uid in seen_uid:
                continue
            seen_uid.add(uid)
        plddt = _to_float(row.get("alphafold_mean_plddt", 0.0), 0.0)
        pinfo = pocket_map.get(uid, {})
        site_res = str(pinfo.get("predicted_binding_site_residues", "")).strip()
        site_conf = _to_float(pinfo.get("heuristic_site_confidence", 0.0), 0.0)
        label = f"Rank {rank} | {drug} | {gene} | {uid}"
        entries.append(
            {
                "id": i,
                "label": label,
                "rank": rank,
                "drug_name": drug,
                "target_gene_symbol": gene,
                "uniprot_id": uid,
                "alphafold_mean_plddt": plddt,
                "predicted_binding_site_residues": site_res,
                "site_confidence": site_conf,
                "pdb_path": str(pdb_path),
                "compact_mode": compact_mode,
                "atom_total": atom_total,
                "atom_kept": atom_kept,
                "pdb": pdb_text,
            }
        )
    return entries


def build_html(entries: list[dict[str, Any]]) -> str:
    payload = json.dumps(entries, ensure_ascii=False)
    template = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AlphaFold 3D Viewer</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", "Noto Sans KR", Arial, sans-serif;
      background: linear-gradient(135deg, #f3f8ff, #eef7f1);
      color: #1f2937;
    }}
    .wrap {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 12px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
      align-items: start;
      min-height: calc(100vh - 24px);
    }}
    .card {{
      background: rgba(255,255,255,0.92);
      border: 1px solid #dbe4ee;
      border-radius: 14px;
      box-shadow: 0 8px 26px rgba(25,35,60,0.08);
    }}
    .panel {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      position: static;
      max-height: none;
    }}
    .top {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      align-items: center;
      padding: 12px;
    }}
    .viewer {{
      height: 62vh;
      min-height: 360px;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid #d6e1ed;
      background: #0b1220;
      position: relative;
      z-index: 0;
    }}
    select, button {{
      border-radius: 10px;
      border: 1px solid #cfd9e7;
      padding: 9px 11px;
      background: white;
      font-size: 14px;
    }}
    button {{
      cursor: pointer;
      font-weight: 600;
    }}
    .meta {{
      padding: 12px;
      font-size: 14px;
      line-height: 1.5;
      overflow: auto;
      max-height: 36vh;
    }}
    .k {{
      display: inline-block;
      min-width: 95px;
      color: #4b5563;
      font-weight: 600;
    }}
    .hint {{
      color: #374151;
      margin-top: 8px;
      font-size: 13px;
    }}
    .status {{
      margin-top: 8px;
      font-size: 13px;
      color: #1f2937;
    }}
    @media (max-width: 980px) {{
      .layout {{
        grid-template-columns: 1fr;
        min-height: auto;
      }}
      .top {{
        grid-template-columns: 1fr;
      }}
      .viewer {{
        height: 52vh;
        min-height: 300px;
      }}
      .meta {{
        max-height: 42vh;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="layout">
      <div class="panel">
        <div class="card top">
          <select id="entrySelect"></select>
          <select id="styleSelect">
            <option value="cartoon_plddt">Cartoon (pLDDT Color)</option>
            <option value="cartoon_chain">Cartoon (Chain Color)</option>
            <option value="stick">Stick</option>
            <option value="sphere">Sphere</option>
          </select>
          <button id="spinBtn">Spin: Off</button>
        </div>
        <div class="status" id="status">Initializing viewer...</div>
        <div class="card meta" id="meta"></div>
      </div>
      <div id="viewer" class="card viewer"></div>
    </div>
  </div>
  <script>
    const entries = __PAYLOAD__;
    const entrySelect = document.getElementById("entrySelect");
    const styleSelect = document.getElementById("styleSelect");
    const spinBtn = document.getElementById("spinBtn");
    const statusEl = document.getElementById("status");
    const meta = document.getElementById("meta");
    const viewerDiv = document.getElementById("viewer");
    let spinOn = false;

    if (!entries.length) {{
      statusEl.textContent = "No structure entries found.";
      viewerDiv.innerHTML = '<div style="padding:20px;color:#111;background:#fff">No structure entries found.</div>';
      meta.innerHTML = '<b>구조 데이터가 없습니다.</b> 입력 CSV와 alphafold_status/alphafold_pdb_path를 확인하세요.';
      throw new Error("No entries");
    }}

    for (let i = 0; i < entries.length; i++) {{
      const op = document.createElement("option");
      op.value = String(i);
      op.textContent = entries[i].label;
      entrySelect.appendChild(op);
    }}

    if (!window.$3Dmol) {{
      statusEl.textContent = "3Dmol.js failed to load.";
      viewerDiv.innerHTML = '<div style="padding:18px;background:#fff;color:#111">3Dmol.js 로딩 실패: 같은 폴더에 3Dmol-min.js가 있는지 확인해주세요.</div>';
      meta.innerHTML = '<b>원인</b>: IAB에서 외부 CDN이 차단되었거나 로컬 스크립트가 없습니다.';
      throw new Error("3Dmol load failed");
    }}

    const viewer = $3Dmol.createViewer("viewer", {{
      backgroundColor: "white",
      antialias: false
    }});
    viewer.resize();
    window.addEventListener("resize", () => {{
      try {{
        viewer.resize();
        viewer.render();
      }} catch (e) {{}}
    }});

    function applyStyle(mode) {{
      viewer.setStyle({{}}, {{}});
      if (mode === "cartoon_chain") {{
        viewer.setStyle({{}}, {{cartoon: {{color: "spectrum"}}}});
      }} else if (mode === "stick") {{
        viewer.setStyle({{}}, {{stick: {{colorscheme: "Jmol"}}}});
      }} else if (mode === "sphere") {{
        viewer.setStyle({{}}, {{sphere: {{colorscheme: "Jmol", scale: 0.28}}}});
      }} else {{
        viewer.setStyle({{}}, {{
          cartoon: {{
            colorscheme: {{
              prop: "b",
              gradient: "rwb",
              min: 0,
              max: 100
            }}
          }}
        }});
      }}
    }}

    function filterPdb(pdbText, mode) {{
      const lines = String(pdbText || "").split(/\\r?\\n/);
      const out = [];
      for (const line of lines) {{
        if (!line) continue;
        if (line.startsWith("ATOM  ")) {{
          const atomName = line.slice(12, 16).trim();
          if (mode === "backbone" && !["N", "CA", "C", "O"].includes(atomName)) continue;
          if (mode === "ca" && atomName !== "CA") continue;
          out.push(line);
          continue;
        }}
        if (line.startsWith("HETATM")) {{
          if (mode === "full") out.push(line);
          continue;
        }}
        if (line.startsWith("TER") || line.startsWith("MODEL ") || line.startsWith("ENDMDL") || line === "END") {{
          out.push(line);
        }}
      }}
      if (out.length > 0 && out[out.length - 1] !== "END") out.push("END");
      return out.join("\\n") + (out.length ? "\\n" : "");
    }}

    function highlightSite(e) {{
      const txt = (e.predicted_binding_site_residues || "").trim();
      if (!txt) return;
      const tokens = txt.split(";").map(x => x.trim()).filter(Boolean);
      for (const t of tokens) {{
        const parts = t.split(":");
        if (parts.length < 2) continue;
        const rc = parts[1]; // e.g., A123
        const chain = rc[0];
        const resi = parseInt(rc.slice(1), 10);
        if (!Number.isFinite(resi)) continue;
        viewer.setStyle({{chain: chain, resi: resi}}, {{stick: {{radius: 0.2, color: "gold"}}}});
      }}
    }}

    function tryRenderModel(pdbText, styleMode, e, doHighlight) {{
      viewer.clear();
      viewer.addModel(pdbText, "pdb");
      applyStyle(styleMode);
      if (doHighlight) highlightSite(e);
      viewer.zoomTo();
      viewer.spin(spinOn);
      viewer.resize();
      viewer.render();
    }}

    function render(index) {{
      const e = entries[index];
      let usedMode = e.compact_mode || "primary";
      statusEl.textContent = "Rendering structure...";
      try {{
        tryRenderModel(e.pdb, styleSelect.value, e, true);
        statusEl.textContent = "Loaded.";
      }} catch (errPrimary) {{
        try {{
          const bb = filterPdb(e.pdb, "backbone");
          tryRenderModel(bb, "stick", e, true);
          usedMode = "fallback_backbone";
          statusEl.textContent = "Fallback Loaded (backbone).";
        }} catch (errBackbone) {{
          try {{
            const ca = filterPdb(e.pdb, "ca");
            tryRenderModel(ca, "stick", e, false);
            usedMode = "fallback_ca";
            statusEl.textContent = "Fallback Loaded (CA-only).";
          }} catch (errCa) {{
            statusEl.textContent = "Render failed: " + String(errCa);
            try {{
              viewer.clear();
              viewer.addSphere({{center: {{x: 0, y: 0, z: 0}}, radius: 1.2, color: "tomato"}});
              viewer.zoomTo();
              viewer.render();
            }} catch (e2) {{}}
          }}
        }}
      }}
      meta.innerHTML = `
        <div><span class="k">Rank</span> ${e.rank || "-"}</div>
        <div><span class="k">Drug</span> ${e.drug_name || "-"}</div>
        <div><span class="k">Target</span> ${e.target_gene_symbol || "-"}</div>
        <div><span class="k">UniProt</span> ${e.uniprot_id || "-"}</div>
        <div><span class="k">Mean pLDDT</span> ${(e.alphafold_mean_plddt || 0).toFixed(2)}</div>
        <div><span class="k">Site Conf</span> ${(e.site_confidence || 0).toFixed(3)}</div>
        <div><span class="k">PDB Path</span> ${e.pdb_path || "-"}</div>
        <div><span class="k">Model Mode</span> ${usedMode}</div>
        <div><span class="k">Atoms</span> ${(e.atom_kept || 0)} / ${(e.atom_total || 0)}</div>
        <div><span class="k">Site Residues</span> ${(e.predicted_binding_site_residues || "-")}</div>
        <div class="hint">마우스 드래그로 회전, 휠로 확대/축소. Cartoon (pLDDT Color)는 B-factor(pLDDT) 기반입니다. 포켓 후보 잔기는 gold stick으로 표시됩니다.</div>
      `;
    }}

    entrySelect.addEventListener("change", () => render(Number(entrySelect.value)));
    styleSelect.addEventListener("change", () => {{
      render(Number(entrySelect.value));
    }});
    spinBtn.addEventListener("click", () => {{
      spinOn = !spinOn;
      viewer.spin(spinOn);
      spinBtn.textContent = `Spin: ${spinOn ? "On" : "Off"}`;
      viewer.render();
    }});

    function pickInitialIndex() {{
      let idx = 0;
      let minAtoms = Number.POSITIVE_INFINITY;
      for (let i = 0; i < entries.length; i++) {{
        const n = Number(entries[i].atom_kept || 0);
        if (n > 0 && n < minAtoms) {{
          minAtoms = n;
          idx = i;
        }}
      }}
      return idx;
    }}

    const initialIndex = pickInitialIndex();
    entrySelect.value = String(initialIndex);
    render(initialIndex);
  </script>
</body>
</html>"""
    # Template was originally authored with doubled braces for f-string escaping.
    # Convert back to normal JS/CSS braces now that we use plain string replacement.
    template = template.replace("{{", "{").replace("}}", "}")
    return template.replace("__PAYLOAD__", payload)


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    pocket_csv = Path(args.pocket_csv) if args.pocket_csv else None
    output_html = Path(args.output_html)
    output_html.parent.mkdir(parents=True, exist_ok=True)

    entries = load_entries(
        input_csv=input_csv,
        pocket_csv=pocket_csv,
        max_items=max(1, args.max_items),
        dedupe_uniprot=bool(args.dedupe_uniprot),
        backbone_threshold_atoms=max(0, int(args.backbone_threshold_atoms)),
    )
    html = build_html(entries)
    output_html.write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "input_csv": str(input_csv),
                "output_html": str(output_html),
                "n_entries": len(entries),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
