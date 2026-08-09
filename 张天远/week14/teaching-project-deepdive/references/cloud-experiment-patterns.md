# Cloud Experiment Orchestration Patterns

Patterns for running multi-model, multi-dataset experiment suites on cloud GPUs with resumability.

## Problem

Running 10+ training+evaluation combinations on a cloud GPU (e.g. AutoDL 4090D). If the script crashes at experiment 7, you don't want to re-run 1-6. If you Ctrl+C to stop, you want to resume later.

## Solution: Marker-based resumption

Each experiment writes a `markers/<exp_id>.done` file on completion. The orchestrator skips experiments whose marker exists.

```bash
MARKER_DIR="markers"
mark_done() { touch "$MARKER_DIR/$1.done"; }
is_done()  { [[ -f "$MARKER_DIR/$1.done" ]]; }

run_step() {
    local id="$1"; local desc="$2"; shift 2
    if is_done "$id"; then echo "  skip $id"; return 0; fi
    echo "── $desc"
    if "$@"; then mark_done "$id"; echo "  done $id"
    else echo "  FAILED ($?) — continuing"; fi
}

# Usage:
run_step "bert_cluener_linear" "BERT+cluener+Linear" \
    python train.py --dataset cluener2020 --epochs 3
```

Key behaviors:
- Ctrl+C kills current experiment, no marker written → auto-retry on next run
- Non-zero exit → skip to next experiment (don't abort the whole suite)
- `rm markers/X.done` + re-run → selectively redo one experiment
- `--dry-run` flag for preview
- Ship `markers/` in the result tarball so you know what succeeded

## Checkpoint naming: model_tag awareness

When running multiple models (bert, roberta) on the same dataset, avoid checkpoint collision by including a model short name in the run_tag:

```python
# train.py / evaluate.py — auto-detect model tag from bert_path
model_path_str = str(args.bert_path).lower()
if "roberta" in model_path_str:
    model_tag = "roberta"
elif "bert" in model_path_str:
    model_tag = ""   # keep backward compat for default
else:
    model_tag = Path(str(args.bert_path)).name[:15]

if args.dataset == "cluener2020":
    if model_tag:
        run_tag = f"{model_tag}_{'crf' if args.use_crf else 'linear'}"
    else:
        run_tag = "crf" if args.use_crf else "linear"  # classic, no change
else:
    prefix = f"{model_tag}_" if model_tag else ""
    run_tag = f"{prefix}{args.dataset}_{'crf' if args.use_crf else 'linear'}"
```

This preserves backward compatibility (bert+cluener → `best_linear.pt` unchanged) while preventing collisions (roberta+cluener → `best_roberta_linear.pt`).

## Full example

See `scripts/cloud_run_all.sh` in Sequence_Labeling project for a complete 10-experiment orchestrator with model downloads, BERT/RoBERTa/QLoRA training, evaluation, summary table generation, auto-logging, autodl-fs persistence, and auto-shutdown.

## Critical Pre-flight Checks

Before running a cloud batch script:
1. **Local smoke-test every model**: `python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('<model>')"` for every model in the batch
2. **Verify all pip packages in download_models list**: missing models → mid-run download failure → no logs
3. **Set up auto-logging**: `exec > >(tee -a "$LOG_FILE") 2>&1` at script start
4. **Copy results to persistent storage**: `/root/autodl-fs/` survives instance release; `/root/autodl-tmp/` does not

## Dependency Auto-install: NEVER reinstall torch/transformers

Cloud images (AutoDL etc.) ship with specific torch + CUDA versions. Running `pip install torch` pulls a different version and breaks CUDA compatibility. **The dependency check must skip torch and transformers entirely:**

```python
# ✅ Correct: only CPU-only lightweight packages
missing = []
for pkg in ['scikit-learn', 'matplotlib', 'tqdm', 'peft', 'datasets']:
    try:
        __import__(pkg_to_import[pkg])
    except ImportError:
        missing.append(pkg)
if missing:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q'] + missing)
```

```python
# ❌ Wrong: including torch/transformers in the list
# This WILL pull a different torch version and break CUDA
for pkg in ['torch', 'transformers', ...]:
```

> ˈIf pip installs a different torch: `ImportError: libcudnn.so.8`, `CUDA error: no kernel image`, or silent CPU fallback.

## Checkpoint naming for ablation experiments

When running hyperparameter sweeps (pool type, layer count, loss type), include experiment parameters in checkpoint filenames to prevent silent overwrites:

```python
# Default config gets short name (backward compatible)
_pool_tag  = f"_{args.pool}" if args.pool != "mean" else ""
_layer_tag = f"_L{args.num_hidden_layers}" if args.num_hidden_layers != 4 else ""
ckpt_name  = f"biencoder_{args.loss}{_pool_tag}{_layer_tag}_best.pt"
# → "biencoder_cosine_best.pt" (default: mean, 4 layers)
# → "biencoder_cosine_cls_best.pt" (pool=cls)
# → "biencoder_cosine_L12_best.pt" (12 layers)
```

Same pattern for log files to ensure training curves aren't overwritten."
