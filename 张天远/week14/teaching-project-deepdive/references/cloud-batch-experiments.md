# Cloud Batch Experiment Pattern

When a project involves 8+ model/dataset combinations that take 5+ hours, a single `cloud_run_all.sh` script with marker-based checkpointing avoids repeated manual restarts.

## Checklist: Before Writing the Script

- [ ] Identify all independent experiment dimensions (model × dataset × head_type)
- [ ] Verify no checkpoint/log filename collisions across dimensions — include model_tag in run_tag if needed
- [ ] Separate local-only experiments (API calls, small GPU) from cloud-only (OOM locally)
- [ ] Estimate total runtime: sum of per-experiment durations (QLoRA 7B ≈ 2h per dataset)

## Script Structure

```bash
# 1. Environment: conda activate + check-imports (skip pre-installed packages)
python -c "
missing = []
for pkg in ['torch', 'transformers', ...]:
    try: __import__(pkg)
    except ImportError: missing.append(pkg)
if missing: subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q'] + missing)
"

# 2. Model download: pre-cache all models before experiments begin
# 3. Experiments: each wrapped in run_step() → writes markers/EXP_ID.done on success
# 4. Summary: auto-generate sorted F1 table from eval_*.json
# 5. Package: tar -czf with checkpoints + logs + markers/
```

## Marker-Based Checkpointing

```bash
mark_done() { touch "$MARKER_DIR/$1.done"; }
is_done()  { [[ -f "$MARKER_DIR/$1.done" ]]; }

run_step() {
    local id="$1"; local desc="$2"; shift 2
    is_done "$id" && { echo "  ⏭ skip"; return 0; }
    echo "── $desc ──"
    if "$@"; then mark_done "$id"; else echo "  ✗ fail — continue"; fi
}

trap 'echo "[!] interrupted"' INT  # graceful Ctrl+C, no .done written
```

Key design decisions:
- Do NOT `set -e` — a single experiment failure must not kill remaining experiments
- Use `set -o pipefail` for pipeline safety without full abort
- Pack `markers/` into the result tarball so downloaded results show completion status
- `--dry-run` flag prints all commands without executing

## Model Comparison Matrix Design

When comparing models of different sizes:
```
序列标注路线                    生成式路线
BERT (102M) × 2 heads          MiniCPM5 (1B) LoRA
RoBERTa (102M) × 2 heads       Qwen2.5 (7B) QLoRA
                                LLM API zero/few-shot
```

Each cell = 2 experiments (×2 datasets). Total: 12 experiments.

## Collision Prevention

Different models on the same dataset must NOT share checkpoint names. Solution:

```python
# train.py: extract model_tag from bert_path
if "roberta" in model_path_str.lower():
    model_tag = "roberta"
elif "bert" in model_path_str.lower():
    model_tag = ""  # default, backward compat
run_tag = f"{model_tag}_{dataset}_{head}" if model_tag else f"{dataset}_{head}"
```

Result: `best_linear.pt`, `best_roberta_linear.pt`, `best_peoples_daily_linear.pt`, `best_roberta_peoples_daily_linear.pt` — zero collisions.
