from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Run the full AlphaFold top-N bundle for any disease: "
            "top candidates -> AlphaFold -> heuristic pocket -> merged annotation -> IAB-safe 3D viewer."
        )
    )
    p.add_argument("--disease", required=True, help="Disease label, used in output folder name")
    p.add_argument("--ranking-json", required=True, help="Input ranking JSON path")
    p.add_argument("--top-n", type=int, default=20, help="Top-N candidates (default: 20)")
    p.add_argument("--max-targets-per-drug", type=int, default=3, help="Max expanded target genes per drug")
    p.add_argument("--out-root", default="analysis", help="Base output root (default: analysis)")
    p.add_argument("--out-dir", default="", help="Optional explicit output directory")
    p.add_argument("--viewer-max-items", type=int, default=20, help="Max entries in viewer")
    p.add_argument("--run-fpocket", action="store_true", help="Run fpocket in topn pipeline (optional)")
    p.add_argument("--dedupe-uniprot", action="store_true", help="Viewer option: one entry per UniProt")
    p.add_argument("--python-exe", default="", help="Optional explicit python executable path")
    p.add_argument("--three-dmol-source", default="", help="Optional local 3Dmol-min.js path to copy")
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--sleep-sec", type=float, default=0.2)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def _slug(s: str) -> str:
    x = re.sub(r"[^a-z0-9]+", "_", s.strip().lower())
    x = x.strip("_")
    return x or "disease"


def _resolve_path(p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def _pick_python(user_python: str) -> str:
    candidates: list[Path] = []
    if user_python:
        candidates.append(_resolve_path(user_python))
    if sys.executable:
        candidates.append(Path(sys.executable))
    candidates.extend(
        [
            ROOT / ".venv" / "Scripts" / "python.exe",
            ROOT / "venv" / "Scripts" / "python.exe",
            ROOT / ".venv" / "bin" / "python",
            ROOT / "venv" / "bin" / "python",
        ]
    )
    for name in ("python", "python3", "py"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    candidates.extend(
        [
            Path(r"C:\Python311\python.exe"),
            Path(r"C:\Python310\python.exe"),
        ]
    )

    seen: set[Path] = set()
    for c in candidates:
        resolved = c.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            return str(resolved.resolve())
    raise FileNotFoundError("Python executable not found. Pass --python-exe explicitly.")


def _fmt_cmd(cmd: Sequence[str]) -> str:
    out: list[str] = []
    for t in cmd:
        if not t:
            continue
        if re.search(r"\s", t):
            out.append(f'"{t}"')
        else:
            out.append(t)
    return " ".join(out)


def _run(cmd: Sequence[str], *, cwd: Path, dry_run: bool) -> None:
    print(f"$ {_fmt_cmd(cmd)}")
    if dry_run:
        return
    subprocess.run(list(cmd), cwd=str(cwd), check=True)


def _copy_3dmol(args: argparse.Namespace, out_dir: Path) -> str:
    dst = out_dir / "3Dmol-min.js"
    if dst.exists():
        return str(dst)

    candidates: list[Path] = []
    if args.three_dmol_source:
        candidates.append(_resolve_path(args.three_dmol_source))
    candidates.extend(
        [
            ROOT / "analysis" / "alphafold_topn_brca_full_v2" / "3Dmol-min.js",
            ROOT / "analysis" / "alphafold_topn_brca_full" / "3Dmol-min.js",
            ROOT / "analysis" / "alphafold_topn_brca" / "3Dmol-min.js",
        ]
    )

    for src in candidates:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return str(dst)
    return ""


def main() -> None:
    args = parse_args()
    disease_slug = _slug(args.disease)
    date_tag = dt.datetime.now().strftime("%Y%m%d")

    ranking_json = _resolve_path(args.ranking_json)
    if not ranking_json.exists():
        raise FileNotFoundError(f"ranking json not found: {ranking_json}")

    if args.out_dir.strip():
        out_dir = _resolve_path(args.out_dir)
    else:
        out_root = _resolve_path(args.out_root)
        out_dir = out_root / f"alphafold_topn_{disease_slug}_{date_tag}"
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    py_exe = _pick_python(args.python_exe)
    topn_script = SCRIPTS_DIR / "alphafold_topn_pipeline.py"
    heuristic_script = SCRIPTS_DIR / "estimate_pocket_residues_heuristic.py"
    merge_script = SCRIPTS_DIR / "merge_site_annotations.py"
    viewer_script = SCRIPTS_DIR / "build_alphafold_3d_viewer_iab_safe.py"

    for s in (topn_script, heuristic_script, merge_script, viewer_script):
        if not s.exists():
            raise FileNotFoundError(f"required script missing: {s}")

    cmd_topn = [
        py_exe,
        str(topn_script),
        "--ranking-json",
        str(ranking_json),
        "--top-n",
        str(max(1, int(args.top_n))),
        "--out-dir",
        str(out_dir),
        "--max-targets-per-drug",
        str(max(1, int(args.max_targets_per_drug))),
        "--retries",
        str(max(0, int(args.retries))),
        "--sleep-sec",
        str(max(0.0, float(args.sleep_sec))),
    ]
    if args.run_fpocket:
        cmd_topn.append("--run-fpocket")
    _run(cmd_topn, cwd=ROOT, dry_run=args.dry_run)

    final_csv = out_dir / "final_top_candidates_with_sites.csv"
    pocket_csv = out_dir / "pocket_sites_heuristic.csv"
    annotated_csv = out_dir / "final_top_candidates_with_sites_annotated.csv"
    summary_md = out_dir / "site_annotation_summary.md"
    viewer_html = out_dir / "alphafold_3d_viewer_with_sites_iab_safe.html"
    viewer_latest = out_dir / "alphafold_3d_viewer_with_sites_latest.html"

    cmd_heuristic = [
        py_exe,
        str(heuristic_script),
        "--input-csv",
        str(final_csv),
        "--output-csv",
        str(pocket_csv),
        "--topk",
        "24",
    ]
    _run(cmd_heuristic, cwd=ROOT, dry_run=args.dry_run)

    cmd_merge = [
        py_exe,
        str(merge_script),
        "--final-csv",
        str(final_csv),
        "--pocket-csv",
        str(pocket_csv),
        "--out-csv",
        str(annotated_csv),
        "--out-md",
        str(summary_md),
    ]
    _run(cmd_merge, cwd=ROOT, dry_run=args.dry_run)

    cmd_viewer = [
        py_exe,
        str(viewer_script),
        "--input-csv",
        str(annotated_csv),
        "--pocket-csv",
        str(pocket_csv),
        "--output-html",
        str(viewer_html),
        "--max-items",
        str(max(1, int(args.viewer_max_items))),
    ]
    if args.dedupe_uniprot:
        cmd_viewer.append("--dedupe-uniprot")
    _run(cmd_viewer, cwd=ROOT, dry_run=args.dry_run)

    if not args.dry_run:
        shutil.copy2(viewer_html, viewer_latest)
        _copy_3dmol(args, out_dir)

    summary = {
        "disease": args.disease,
        "disease_slug": disease_slug,
        "input_ranking_json": str(ranking_json),
        "output_dir": str(out_dir),
        "python_executable": py_exe,
        "outputs": {
            "top_candidates_csv": str(out_dir / "top_candidates.csv"),
            "target_pairs_csv": str(out_dir / "top_candidate_target_pairs.csv"),
            "target_uniprot_map_csv": str(out_dir / "target_uniprot_map.csv"),
            "alphafold_models_csv": str(out_dir / "alphafold_models.csv"),
            "final_csv": str(final_csv),
            "heuristic_pocket_csv": str(pocket_csv),
            "annotated_csv": str(annotated_csv),
            "summary_md": str(summary_md),
            "viewer_html": str(viewer_html),
            "viewer_latest_html": str(viewer_latest),
            "viewer_3dmol_js": str(out_dir / "3Dmol-min.js"),
        },
        "commands": {
            "topn": _fmt_cmd(cmd_topn),
            "heuristic": _fmt_cmd(cmd_heuristic),
            "merge": _fmt_cmd(cmd_merge),
            "viewer": _fmt_cmd(cmd_viewer),
        },
        "dry_run": bool(args.dry_run),
    }

    summary_path = out_dir / "auto_bundle_summary.json"
    if not args.dry_run:
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
