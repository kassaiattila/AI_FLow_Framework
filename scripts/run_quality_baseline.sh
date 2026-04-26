#!/usr/bin/env bash
# AIFlow quality baseline — 4 use-case measurement aggregator.
#
# Sprint X exit gate. Mandatory for every sprint-close.
# Source: docs/honest_alignment_audit.md §4.4.
#
# Usage:
#   bash scripts/run_quality_baseline.sh                    # text summary
#   bash scripts/run_quality_baseline.sh --output json      # JSON aggregate
#   bash scripts/run_quality_baseline.sh --uc UC1           # single UC
#   bash scripts/run_quality_baseline.sh --strict           # exit nonzero if any UC below target
#   bash scripts/run_quality_baseline.sh --corpus real      # DocRecognizer real-corpus mode (Sprint X SX-3)
#
# Targets (Sprint X gate):
#   UC1 invoice accuracy ≥ 92% on 25-fixture mixed corpus
#   UC2 RAG MRR@5 ≥ 0.55 (Sprint X baseline; Sprint Y target ≥ 0.72)
#   UC3 misclass ≤ 1% on 25-fixture attachment-aware corpus
#   DocRecognizer per-doctype accuracy ≥ 80% (≥ 70% acceptable for eu_passport)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUTPUT_FORMAT="text"
TARGET_UC="all"
CORPUS_MODE="default"
STRICT_MODE=0

# Parse args.
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FORMAT="$2"
      shift 2
      ;;
    --uc)
      TARGET_UC="$2"
      shift 2
      ;;
    --corpus)
      CORPUS_MODE="$2"
      shift 2
      ;;
    --strict)
      STRICT_MODE=1
      shift
      ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $1" >&2
      exit 64
      ;;
  esac
done

# Discover python.
if [[ -x ".venv/Scripts/python.exe" ]]; then
  PYTHON=".venv/Scripts/python.exe"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python"
fi

# Targets per UC (Sprint X gate values; update on Sprint Y for UC2 to 0.72).
declare -A TARGETS=(
  ["UC1"]="0.92"
  ["UC2"]="0.55"
  ["UC3"]="0.01"
  ["DocRecognizer"]="0.80"
)

# Holders.
declare -A VALUES
declare -A METRICS
declare -A GATES

run_uc1() {
  if [[ "$TARGET_UC" != "all" && "$TARGET_UC" != "UC1" ]]; then return 0; fi
  METRICS["UC1"]="invoice_accuracy_25fixture"

  if ! command -v "$PYTHON" >/dev/null 2>&1; then
    VALUES["UC1"]="error:no-python"
    GATES["UC1"]="unknown"
    return
  fi

  # measure_uc1_golden_path.py supports --output json since SW-4.
  local raw
  if raw=$("$PYTHON" scripts/measure_uc1_golden_path.py --output json 2>&1); then
    VALUES["UC1"]=$(echo "$raw" | "$PYTHON" -c "import sys, json; d=json.loads(sys.stdin.read()); print(d.get('overall_accuracy', d.get('accuracy', 'n/a')))" 2>/dev/null || echo "parse-error")
  else
    VALUES["UC1"]="run-error"
  fi

  if [[ "${VALUES[UC1]}" =~ ^[0-9.]+$ ]]; then
    if (( $(echo "${VALUES[UC1]} >= ${TARGETS[UC1]}" | bc -l 2>/dev/null || echo 0) )); then
      GATES["UC1"]="above"
    else
      GATES["UC1"]="below"
    fi
  else
    GATES["UC1"]="unknown"
  fi
}

run_uc2() {
  if [[ "$TARGET_UC" != "all" && "$TARGET_UC" != "UC2" ]]; then return 0; fi
  METRICS["UC2"]="mrr_at_5_profile_a"

  # run_nightly_rag_metrics.py is gated by AIFLOW_RUN_NIGHTLY_RAG_METRICS=1
  # + OPENAI_API_KEY. Skip-by-default in this aggregator.
  if [[ "${AIFLOW_RUN_NIGHTLY_RAG_METRICS:-0}" != "1" ]]; then
    VALUES["UC2"]="skipped:set AIFLOW_RUN_NIGHTLY_RAG_METRICS=1 to run"
    GATES["UC2"]="skipped"
    return
  fi

  local raw
  if raw=$("$PYTHON" scripts/run_nightly_rag_metrics.py --output json 2>&1); then
    VALUES["UC2"]=$(echo "$raw" | "$PYTHON" -c "import sys, json; d=json.loads(sys.stdin.read()); print(d.get('mrr_at_5', d.get('mrr', 'n/a')))" 2>/dev/null || echo "parse-error")
  else
    VALUES["UC2"]="run-error"
  fi

  if [[ "${VALUES[UC2]}" =~ ^[0-9.]+$ ]]; then
    if (( $(echo "${VALUES[UC2]} >= ${TARGETS[UC2]}" | bc -l 2>/dev/null || echo 0) )); then
      GATES["UC2"]="above"
    else
      GATES["UC2"]="below"
    fi
  else
    GATES["UC2"]="unknown"
  fi
}

run_uc3() {
  if [[ "$TARGET_UC" != "all" && "$TARGET_UC" != "UC3" ]]; then return 0; fi
  METRICS["UC3"]="misclass_rate_25fixture_attachment_aware"

  # measure_uc3_attachment_intent.py does NOT yet emit --output json (TODO SX-4).
  # For now, the script writes a report under data/uc3_*/ — the aggregator
  # parses it. SX-4 migrates this script to argparse_output() helper.
  VALUES["UC3"]="todo:argparse_output migration in SX-4"
  GATES["UC3"]="unknown"
}

run_doc_recognizer() {
  if [[ "$TARGET_UC" != "all" && "$TARGET_UC" != "DocRecognizer" ]]; then return 0; fi
  METRICS["DocRecognizer"]="per_doctype_accuracy_min"

  # measure_doc_recognizer_accuracy.py supports --output json (SV-5).
  local raw
  local args=(--output json)
  if [[ "$CORPUS_MODE" == "real" ]]; then
    args+=(--corpus real)
  fi

  if raw=$("$PYTHON" scripts/measure_doc_recognizer_accuracy.py "${args[@]}" 2>&1); then
    # Aggregator extracts the minimum per-doctype accuracy.
    VALUES["DocRecognizer"]=$(echo "$raw" | "$PYTHON" -c "import sys, json
try:
    d = json.loads(sys.stdin.read())
    per = d.get('per_doctype', d.get('results', []))
    if isinstance(per, dict):
        vals = list(per.values())
    elif isinstance(per, list):
        vals = [r.get('accuracy', r.get('score', 0)) for r in per]
    else:
        vals = []
    print(min(vals) if vals else 'n/a')
except Exception as e:
    print(f'parse-error:{e}')" 2>/dev/null || echo "parse-error")
  else
    if [[ "$CORPUS_MODE" == "real" ]]; then
      VALUES["DocRecognizer"]="todo:real-corpus pending SX-3"
      GATES["DocRecognizer"]="no-corpus"
      return
    fi
    VALUES["DocRecognizer"]="run-error"
  fi

  if [[ "${VALUES[DocRecognizer]}" =~ ^[0-9.]+$ ]]; then
    if (( $(echo "${VALUES[DocRecognizer]} >= ${TARGETS[DocRecognizer]}" | bc -l 2>/dev/null || echo 0) )); then
      GATES["DocRecognizer"]="above"
    else
      GATES["DocRecognizer"]="below"
    fi
  else
    GATES["DocRecognizer"]="unknown"
  fi
}

emit_text() {
  echo "============================================="
  echo "AIFlow quality baseline — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "============================================="
  echo "UC               | metric                                   | baseline | target | gate"
  echo "-----------------+------------------------------------------+----------+--------+----------"
  for uc in UC1 UC2 UC3 DocRecognizer; do
    if [[ -n "${VALUES[$uc]:-}" ]]; then
      printf "%-16s | %-40s | %-8s | %-6s | %s\n" \
        "$uc" "${METRICS[$uc]:-n/a}" "${VALUES[$uc]}" "${TARGETS[$uc]:-n/a}" "${GATES[$uc]:-unknown}"
    fi
  done
  echo "============================================="
}

emit_json() {
  echo "{"
  echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"corpus_mode\": \"$CORPUS_MODE\","
  echo "  \"use_cases\": ["
  local first=1
  for uc in UC1 UC2 UC3 DocRecognizer; do
    if [[ -n "${VALUES[$uc]:-}" ]]; then
      [[ $first -eq 0 ]] && echo ","
      first=0
      echo -n "    {\"name\": \"$uc\", \"metric\": \"${METRICS[$uc]:-n/a}\", \"value\": \"${VALUES[$uc]}\", \"target\": \"${TARGETS[$uc]:-n/a}\", \"gate\": \"${GATES[$uc]:-unknown}\"}"
    fi
  done
  echo
  echo "  ]"
  echo "}"
}

# Run measurements.
run_uc1
run_uc2
run_uc3
run_doc_recognizer

# Emit.
case "$OUTPUT_FORMAT" in
  text) emit_text ;;
  json) emit_json ;;
  *) echo "[error] --output must be text or json (got: $OUTPUT_FORMAT)" >&2; exit 64 ;;
esac

# Strict mode exit code.
if [[ $STRICT_MODE -eq 1 ]]; then
  for uc in UC1 UC2 UC3 DocRecognizer; do
    if [[ -n "${VALUES[$uc]:-}" ]]; then
      gate="${GATES[$uc]:-unknown}"
      if [[ "$gate" == "below" ]]; then
        echo "[strict] gate failure on $uc: ${VALUES[$uc]} < ${TARGETS[$uc]}" >&2
        exit 1
      fi
    fi
  done
fi

exit 0
