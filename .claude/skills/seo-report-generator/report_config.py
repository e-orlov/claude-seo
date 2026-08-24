"""
report_config.py
════════════════
Output path resolution for SEO report scripts.

No client-specific data allowed in this file.
Every gen_*.py calls resolve_output_path(cfg) to determine where to save the .docx.

Resolution priority (first match wins):
  1. cfg["output_dir"] — explicitly set in the script's CFG dict
  2. Environment variable SEO_REPORT_OUTPUT_DIR
  3. <cwd>/clients/<domain>/<date_slug>/output/  — project workspace convention
  4. <script directory>/output/<domain>/          — fallback if no clients/ structure exists

The resolved directory is created automatically if it does not exist.
"""

import os
from pathlib import Path


def resolve_output_path(cfg: dict) -> Path:
    """
    Determine the output directory for a report and return the full .docx path.

    Args:
        cfg: ReportConfig dict. Required keys:
               domain      — e.g. "pyroweb.de"
               report_name — filename stem, e.g. "Interne_Weiterleitungen"
               date_slug   — e.g. "2026-06"
             Optional keys:
               output_dir  — explicit absolute path string; skips all other resolution

    Returns:
        Full Path to the .docx output file, e.g.:
        .../clients/pyroweb.de/2026-06/output/Interne_Weiterleitungen_2026-06.docx

    Raises:
        ValueError: if required keys are missing from cfg
    """
    for key in ("domain", "report_name", "date_slug"):
        if not cfg.get(key):
            raise ValueError(
                f"resolve_output_path: cfg['{key}'] is required but missing or empty."
            )

    filename = f"{cfg['report_name']}_{cfg['date_slug']}.docx"

    # 1. Explicit override in CFG
    if cfg.get("output_dir"):
        out_dir = Path(cfg["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / filename

    # 2. Environment variable
    if env_dir := os.environ.get("SEO_REPORT_OUTPUT_DIR"):
        out_dir = Path(env_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / filename

    # 3. Project workspace: clients/<domain>/<date_slug>/output/
    # Walk up from cwd to find a 'clients' directory (handles running from any subdir)
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        clients_dir = candidate / "clients"
        if clients_dir.is_dir():
            out_dir = clients_dir / cfg["domain"] / cfg["date_slug"] / "output"
            out_dir.mkdir(parents=True, exist_ok=True)
            return out_dir / filename

    # 4. Fallback: <script cwd>/output/<domain>/
    out_dir = cwd / "output" / cfg["domain"]
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename
