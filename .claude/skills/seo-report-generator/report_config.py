"""
report_config.py
════════════════
Output path resolution for SEO report scripts.

No client-specific data allowed in this file.
Every gen_*.py calls resolve_output_path(cfg) to determine where to save the .docx.

Every report has its own folder, named after cfg["report_name"]. The .docx and all
exports that belong to the report are saved there.

Resolution priority (first match wins):
  1. cfg["output_dir"] — explicitly set in the script's CFG dict; used exactly as given
  2. Environment variable SEO_REPORT_OUTPUT_DIR, plus /<report_name>/
  3. <cwd>/clients/<domain>/<date_slug>/output/<report_name>/ — project workspace convention
  4. <cwd>/output/<domain>/<report_name>/    — fallback if no clients/ structure exists

The resolved directory is created automatically if it does not exist.
"""

import os
from pathlib import Path


def resolve_report_dir(cfg: dict) -> Path:
    """
    Return (and create) the folder for one report and its exports.

    Args:
        cfg: ReportConfig dict. Required keys:
               domain      — e.g. "pyroweb.de"
               report_name — folder name and filename stem, e.g. "Interne_Weiterleitungen"
               date_slug   — e.g. "2026-06"
             Optional keys:
               output_dir  — explicit absolute path string; skips all other resolution

    Raises:
        ValueError: if required keys are missing from cfg
    """
    for key in ("domain", "report_name", "date_slug"):
        if not cfg.get(key):
            raise ValueError(
                f"resolve_report_dir: cfg['{key}'] is required but missing or empty."
            )

    if cfg.get("output_dir"):
        # 1. Explicit override in CFG
        out_dir = Path(cfg["output_dir"])
    elif env_dir := os.environ.get("SEO_REPORT_OUTPUT_DIR"):
        # 2. Environment variable
        out_dir = Path(env_dir) / cfg["report_name"]
    else:
        # 3. Project workspace; walk up from cwd to find a 'clients' directory
        cwd = Path.cwd()
        for candidate in [cwd, *cwd.parents]:
            clients_dir = candidate / "clients"
            if clients_dir.is_dir():
                out_dir = (clients_dir / cfg["domain"] / cfg["date_slug"] / "output"
                           / cfg["report_name"])
                break
        else:
            # 4. Fallback
            out_dir = cwd / "output" / cfg["domain"] / cfg["report_name"]

    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def resolve_output_path(cfg: dict) -> Path:
    """
    Return the full .docx path, e.g.:
    .../clients/pyroweb.de/2026-06/output/Interne_Weiterleitungen/Interne_Weiterleitungen_2026-06.docx
    """
    return resolve_report_dir(cfg) / f"{cfg['report_name']}_{cfg['date_slug']}.docx"
