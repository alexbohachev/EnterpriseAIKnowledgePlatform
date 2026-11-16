#!/usr/bin/env python3
"""Stage7 limited preflight; not a substitute for Docker/LLM acceptance."""
from pathlib import Path
import json, shutil, subprocess, sys

root = Path(__file__).resolve().parents[1]
files = ["app/main.py", "app/rag/workflow.py", "app/rag/query.py",
         "app/worker.py", "compose.yaml", "Dockerfile", "alembic.ini",
         "monitoring/prometheus/prometheus.yml",
         "docs/Stage7_Requirements_Traceability_UA.md",
         "presentation/EAKP_OTUS_Defense_UA.pptx"]
missing = [str(f) for f in files if not (root/f).is_file()]
record = {"offline_preflight":True,"missing_files":missing,
          "docker_executable_available":bool(shutil.which("docker")),
          "unit_tests": "not run",
          "limitations": "static files + pytest only; no real Docker, ACL E2E, air-gap or LLM load test"}
try:
    import yaml
    with (root/"compose.yaml").open(encoding="utf-8") as f:
        record["compose_yaml_parse"] = "PASS" if isinstance(yaml.safe_load(f), dict) else "FAIL"
except Exception as e:
    record["compose_yaml_parse"] = f"UNVERIFIED: {type(e).__name__}"
try:
    p = subprocess.run([sys.executable,"-m","pytest","-q"],cwd=root,
                       text=True,capture_output=True,timeout=120)
    record["unit_tests"] = "PASS" if p.returncode == 0 else "FAIL"
    record["pytest_stdout_tail"] = p.stdout.strip()[-180:]
    record["pytest_exit_code"] = p.returncode
except Exception as e:
    record["unit_tests"] = f"UNVERIFIED: {type(e).__name__}"
(root/"reports"/"stage7_preflight.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(record,ensure_ascii=False,indent=2))
raise SystemExit(1 if missing or record["unit_tests"] == "FAIL" or record.get("compose_yaml_parse") == "FAIL" else 0)
