from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build IAB-safe AlphaFold 3D viewer HTML")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--pocket-csv", default="")
    p.add_argument("--output-html", required=True)
    p.add_argument("--max-items", type=int, default=20)
    p.add_argument("--dedupe-uniprot", action="store_true")
    p.add_argument("--backbone-threshold-atoms", type=int, default=1)
    return p.parse_args()


def _to_float(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return d


def _to_int(v: Any, d: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return d


def compact_pdb(pdb_text: str, backbone_threshold_atoms: int) -> tuple[str, str, int, int]:
    lines = pdb_text.splitlines()
    atom_total = sum(1 for ln in lines if ln.startswith("ATOM  "))
    use_backbone = atom_total > max(0, backbone_threshold_atoms)
    out: list[str] = []
    atom_kept = 0
    for ln in lines:
        if ln.startswith("ATOM  "):
            if use_backbone:
                atom = ln[12:16].strip()
                if atom not in {"N", "CA", "C", "O"}:
                    continue
            out.append(ln)
            atom_kept += 1
            continue
        if ln.startswith("HETATM"):
            if not use_backbone:
                out.append(ln)
            continue
        if ln.startswith("TER") or ln.startswith("MODEL ") or ln.startswith("ENDMDL") or ln == "END":
            out.append(ln)
    if out and out[-1] != "END":
        out.append("END")
    mode = "backbone_only" if use_backbone else "full_atoms"
    return ("\n".join(out) + ("\n" if out else "")), mode, atom_total, atom_kept


def load_entries(args: argparse.Namespace) -> list[dict[str, Any]]:
    df = pd.read_csv(args.input_csv)
    pocket_map: dict[str, dict[str, Any]] = {}
    if args.pocket_csv:
        p = Path(args.pocket_csv)
        if p.exists():
            dfp = pd.read_csv(p)
            if "uniprot_id" in dfp.columns:
                for _, r in dfp.iterrows():
                    uid = str(r.get("uniprot_id", "")).strip()
                    if not uid:
                        continue
                    pocket_map[uid] = {
                        "site": str(r.get("predicted_binding_site_residues", "")).strip(),
                        "conf": _to_float(r.get("heuristic_site_confidence", 0.0), 0.0),
                    }

    keep = df[
        (df.get("alphafold_status", "").astype(str) == "ok")
        & (df.get("alphafold_pdb_path", "").astype(str).str.len() > 0)
    ].copy()
    keep = keep.head(max(1, args.max_items))

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in keep.iterrows():
        uid = str(row.get("uniprot_id", "")).strip()
        if args.dedupe_uniprot and uid:
            if uid in seen:
                continue
            seen.add(uid)
        pdb_path = Path(str(row.get("alphafold_pdb_path", "")).strip())
        if not pdb_path.exists():
            continue
        pdb_raw = pdb_path.read_text(encoding="utf-8", errors="ignore")
        pdb_txt, mode, atom_total, atom_kept = compact_pdb(pdb_raw, args.backbone_threshold_atoms)
        pinfo = pocket_map.get(uid, {})
        out.append(
            {
                "id": int(i),
                "label": f"Rank {_to_int(row.get('rank', 0), 0)} | {str(row.get('drug_name', '')).strip()} | {str(row.get('target_gene_symbol', '')).strip()} | {uid}",
                "rank": _to_int(row.get("rank", 0), 0),
                "drug_name": str(row.get("drug_name", "")).strip(),
                "target_gene_symbol": str(row.get("target_gene_symbol", "")).strip(),
                "uniprot_id": uid,
                "alphafold_mean_plddt": _to_float(row.get("alphafold_mean_plddt", 0.0), 0.0),
                "predicted_binding_site_residues": str(pinfo.get("site", "")).strip(),
                "site_confidence": _to_float(pinfo.get("conf", 0.0), 0.0),
                "compact_mode": mode,
                "atom_total": atom_total,
                "atom_kept": atom_kept,
                "pdb": pdb_txt,
            }
        )
    return out


def build_html(entries: list[dict[str, Any]]) -> str:
    payload = json.dumps(entries, ensure_ascii=False)
    template = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AlphaFold 3D Viewer (IAB Safe)</title>
  <style>
    body {
      margin: 0;
      font-family: "Segoe UI", "Noto Sans KR", Arial, sans-serif;
      background: linear-gradient(135deg, #f3f8ff, #eef7f1);
      color: #1f2937;
    }
    .wrap { max-width: 1300px; margin: 0 auto; padding: 12px; }
    .card {
      background: rgba(255,255,255,0.94);
      border: 1px solid #dbe4ee;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(25,35,60,0.08);
    }
    .layout {
      display: grid;
      gap: 10px;
      align-items: start;
    }
    .layout.right { grid-template-columns: 380px 1fr; }
    .layout.right .panel { order: 1; }
    .layout.right .viewer { order: 2; }
    .layout.top { grid-template-columns: 1fr; }
    .layout.top .viewer { order: 1; }
    .layout.top .panel { order: 2; }
    .layout.bottom { grid-template-columns: 1fr; }
    .layout.bottom .panel { order: 1; }
    .layout.bottom .viewer { order: 2; }
    .panel {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .toolbar {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      padding: 10px;
    }
    .subbar {
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 8px;
      padding: 10px;
    }
    .viewer {
      height: 70vh;
      min-height: 420px;
      border: 1px solid #d6e1ed;
      border-radius: 12px;
      overflow: hidden;
      background: #0b1220;
    }
    .status { margin: 8px 2px; font-size: 13px; color: #374151; }
    .meta {
      margin-top: 10px;
      padding: 10px;
      font-size: 14px;
      line-height: 1.45;
      max-height: 30vh;
      overflow: auto;
    }
    .k { display: inline-block; min-width: 100px; color: #4b5563; font-weight: 600; }
    select, button {
      border-radius: 10px;
      border: 1px solid #cfd9e7;
      padding: 8px 10px;
      background: #fff;
      font-size: 14px;
    }
    @media (max-width: 900px) {
      .layout { grid-template-columns: 1fr !important; }
      .toolbar { grid-template-columns: 1fr; }
      .subbar { grid-template-columns: 1fr; }
      .viewer { height: 52vh; min-height: 300px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div id="layout" class="layout right">
      <div class="panel">
        <div class="card toolbar">
          <select id="entrySelect"></select>
          <select id="styleSelect">
            <option value="cartoon_plddt">Cartoon (pLDDT Color)</option>
            <option value="cartoon_chain">Cartoon (Chain Color)</option>
            <option value="stick">Stick</option>
            <option value="sphere">Sphere</option>
          </select>
        </div>
        <div class="card subbar">
          <select id="positionSelect">
            <option value="right">3D 오른쪽</option>
            <option value="top">3D 위</option>
            <option value="bottom">3D 아래</option>
          </select>
          <button id="spinBtn">Spin: Off</button>
          <button id="activateBtn">3D 다시 시도</button>
        </div>
        <div class="status" id="status">Initializing viewer...</div>
        <div id="meta" class="card meta"></div>
      </div>
      <div id="viewer" class="card viewer"></div>
    </div>
  </div>
  <script>
    const entries = __PAYLOAD__;
    const layoutEl = document.getElementById("layout");
    const entrySelect = document.getElementById("entrySelect");
    const styleSelect = document.getElementById("styleSelect");
    const positionSelect = document.getElementById("positionSelect");
    const spinBtn = document.getElementById("spinBtn");
    const activateBtn = document.getElementById("activateBtn");
    const statusEl = document.getElementById("status");
    const metaEl = document.getElementById("meta");
    const viewerEl = document.getElementById("viewer");
    let viewer = null;
    let spinOn = false;
    let uiBound = false;
    let booting = false;

    function setStatus(msg) { statusEl.textContent = msg; }
    function applyLayout(pos) { layoutEl.className = "layout " + (pos || "right"); }

    function loadScript(src, timeoutMs) {
      return new Promise((resolve, reject) => {
        const s = document.createElement("script");
        let done = false;
        const t = setTimeout(() => {
          if (done) return;
          done = true;
          s.remove();
          reject(new Error("timeout: " + src));
        }, timeoutMs || 8000);
        s.src = src;
        s.onload = () => {
          if (done) return;
          done = true;
          clearTimeout(t);
          resolve();
        };
        s.onerror = () => {
          if (done) return;
          done = true;
          clearTimeout(t);
          reject(new Error("load failed: " + src));
        };
        document.head.appendChild(s);
      });
    }

    async function ensure3Dmol() {
      if (window.$3Dmol) return;
      try {
        await loadScript("./3Dmol-min.js", 6000);
      } catch (e1) {
        await loadScript("https://3Dmol.org/build/3Dmol-min.js", 8000);
      }
      if (!window.$3Dmol) throw new Error("3Dmol unavailable");
    }

    function canUseWebGL() {
      try {
        const c = document.createElement("canvas");
        const gl = c.getContext("webgl") || c.getContext("experimental-webgl");
        return !!gl;
      } catch (e) {
        return false;
      }
    }

    function installWebGL2FallbackHack() {
      try {
        if (window.__webgl2_fallback_installed) return;
        const proto = HTMLCanvasElement && HTMLCanvasElement.prototype;
        if (!proto || !proto.getContext) return;
        const original = proto.getContext;
        proto.getContext = function(type, attrs) {
          if (type === "webgl2") {
            const gl1 = original.call(this, "webgl", attrs) || original.call(this, "experimental-webgl", attrs);
            if (gl1) return gl1;
          }
          return original.call(this, type, attrs);
        };
        window.__webgl2_fallback_installed = true;
      } catch (e) {}
    }

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

    function filterPdb(pdbText, mode) {
      const lines = String(pdbText || "").split(/\\r?\\n/);
      const out = [];
      for (const line of lines) {
        if (!line) continue;
        if (line.startsWith("ATOM  ")) {
          const atom = line.slice(12, 16).trim();
          if (mode === "backbone" && !["N", "CA", "C", "O"].includes(atom)) continue;
          if (mode === "ca" && atom !== "CA") continue;
          out.push(line);
          continue;
        }
        if (line.startsWith("HETATM")) {
          if (mode === "full") out.push(line);
          continue;
        }
        if (line.startsWith("TER") || line.startsWith("MODEL ") || line.startsWith("ENDMDL") || line === "END") out.push(line);
      }
      if (out.length && out[out.length - 1] !== "END") out.push("END");
      return out.join("\\n") + (out.length ? "\\n" : "");
    }

    function highlightSite(e) {
      const txt = (e.predicted_binding_site_residues || "").trim();
      if (!txt) return;
      const tokens = txt.split(";").map(x => x.trim()).filter(Boolean);
      for (const t of tokens) {
        const parts = t.split(":");
        if (parts.length < 2) continue;
        const rc = parts[1];
        const chain = rc[0];
        const resi = parseInt(rc.slice(1), 10);
        if (!Number.isFinite(resi)) continue;
        viewer.setStyle({ chain: chain, resi: resi }, { stick: { radius: 0.2, color: "gold" } });
      }
    }

    function tryRenderModel(pdbText, styleMode, e, doHighlight) {
      viewer.clear();
      viewer.addModel(pdbText, "pdb");
      applyStyle(styleMode);
      if (doHighlight) highlightSite(e);
      viewer.zoomTo();
      viewer.spin(spinOn);
      viewer.resize();
      viewer.render();
    }

    function render(index) {
      const e = entries[index];
      let modeUsed = e.compact_mode || "primary";
      setStatus("Rendering structure...");
      try {
        tryRenderModel(e.pdb, styleSelect.value, e, true);
        setStatus("Loaded.");
      } catch (errPrimary) {
        try {
          const bb = filterPdb(e.pdb, "backbone");
          tryRenderModel(bb, "stick", e, true);
          modeUsed = "fallback_backbone";
          setStatus("Fallback Loaded (backbone).");
        } catch (errBackbone) {
          try {
            const ca = filterPdb(e.pdb, "ca");
            tryRenderModel(ca, "stick", e, false);
            modeUsed = "fallback_ca";
            setStatus("Fallback Loaded (CA-only).");
          } catch (errCa) {
            setStatus("Render failed: " + String(errCa));
            try {
              viewer.clear();
              viewer.addSphere({ center: {x: 0, y: 0, z: 0}, radius: 1.2, color: "tomato" });
              viewer.zoomTo();
              viewer.render();
            } catch (e2) {}
          }
        }
      }

      metaEl.innerHTML = `
        <div><span class="k">Rank</span> ${e.rank || "-"}</div>
        <div><span class="k">Drug</span> ${e.drug_name || "-"}</div>
        <div><span class="k">Target</span> ${e.target_gene_symbol || "-"}</div>
        <div><span class="k">UniProt</span> ${e.uniprot_id || "-"}</div>
        <div><span class="k">Mean pLDDT</span> ${(e.alphafold_mean_plddt || 0).toFixed(2)}</div>
        <div><span class="k">Site Conf</span> ${(e.site_confidence || 0).toFixed(3)}</div>
        <div><span class="k">Mode</span> ${modeUsed}</div>
        <div><span class="k">Atoms</span> ${(e.atom_kept || 0)} / ${(e.atom_total || 0)}</div>
      `;
    }

    function pickInitialIndex() {
      let idx = 0;
      let minAtoms = Number.POSITIVE_INFINITY;
      for (let i = 0; i < entries.length; i++) {
        const n = Number(entries[i].atom_kept || 0);
        if (n > 0 && n < minAtoms) {
          minAtoms = n;
          idx = i;
        }
      }
      return idx;
    }

    function bindUI() {
      if (uiBound) return;
      uiBound = true;
      for (let i = 0; i < entries.length; i++) {
        const op = document.createElement("option");
        op.value = String(i);
        op.textContent = entries[i].label;
        entrySelect.appendChild(op);
      }
      positionSelect.addEventListener("change", () => applyLayout(positionSelect.value));
      entrySelect.addEventListener("change", () => render(Number(entrySelect.value)));
      styleSelect.addEventListener("change", () => render(Number(entrySelect.value)));
      spinBtn.addEventListener("click", () => {
        spinOn = !spinOn;
        spinBtn.textContent = `Spin: ${spinOn ? "On" : "Off"}`;
        if (viewer) {
          viewer.spin(spinOn);
          viewer.render();
        }
      });
      activateBtn.addEventListener("click", () => {
        if (viewer) {
          render(Number(entrySelect.value || 0));
        } else {
          bootstrap(true);
        }
      });
    }

    async function bootstrap(fromRetry) {
      if (booting) return;
      booting = true;
      if (!entries.length) {
        setStatus("No structure entries found.");
        booting = false;
        return;
      }
      applyLayout(positionSelect.value || "right");
      bindUI();
      setStatus("Loading 3D engine...");
      try {
        await ensure3Dmol();
      } catch (e) {
        setStatus("3D engine load failed: " + String(e));
        booting = false;
        return;
      }
      if (!canUseWebGL()) {
        setStatus("WebGL unavailable in current IAB. Open same file in Chrome.");
        metaEl.innerHTML = "<b>WebGL unsupported.</b> Please open this file in Chrome/Edge.";
        booting = false;
        return;
      }
      try {
        installWebGL2FallbackHack();
        viewerEl.innerHTML = "";
        viewer = $3Dmol.createViewer("viewer", { backgroundColor: "white", antialias: false });
        viewer.resize();
      } catch (e) {
        const msg = String(e || "");
        viewer = null;
        if (msg.includes("clearDepth") || msg.includes("creating viewer")) {
          try {
            installWebGL2FallbackHack();
            viewerEl.innerHTML = "";
            viewer = $3Dmol.createViewer("viewer", { backgroundColor: "white", antialias: false });
            viewer.resize();
            setStatus("Viewer initialized with WebGL fallback.");
          } catch (e2) {
            viewer = null;
            setStatus("Viewer init failed: " + String(e2));
            metaEl.innerHTML = "<b>WebGL init failed.</b> IAB may block 3D context; try Chrome.";
            booting = false;
            return;
          }
        } else {
          setStatus("Viewer init failed: " + msg);
          booting = false;
          return;
        }
      }
      window.addEventListener("resize", () => { try { viewer.resize(); viewer.render(); } catch (e) {} });
      const idx = pickInitialIndex();
      entrySelect.value = String(idx);
      render(idx);
      if (fromRetry) setStatus("Loaded after retry.");
      booting = false;
    }

    bootstrap();
  </script>
</body>
</html>"""
    return template.replace("__PAYLOAD__", payload)


def main() -> None:
    args = parse_args()
    entries = load_entries(args)
    out = Path(args.output_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(entries), encoding="utf-8")
    print(json.dumps({"output_html": str(out), "n_entries": len(entries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
