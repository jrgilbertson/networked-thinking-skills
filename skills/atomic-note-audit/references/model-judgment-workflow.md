# Model judgment workflow

Run these commands from the installed `atomic-note-audit` skill root, after
creating and validating the deterministic audit JSONL and manifest.

Use `references/model-judgment-prompt.md` verbatim when asking an
LLM for model judgment. The prompt is generated from the scoring vocabulary
source of truth and must stay aligned with `scripts/finding_codes.py`.
Model output must be strict JSON and validated before it affects scoring.
The collector owns stored schema and prompt provenance; do not ask the model to
invent those values.

## Inspect one note

To inspect the generated content prompt for one note, run:

```bash
python3 scripts/prepare_model_judgment.py --vault /path/to/vault --note-path "Atomic Notes/Example.md" --output /tmp/model-judgment-request.md
```

## Collect one judgment

The prompt and the model's raw response are inspection artifacts. To produce a
validated judgment that can affect scoring, select the note's audit row and use
the batch collector:

```bash
python3 scripts/prepare_model_judgment.py --vault /path/to/vault --note-path "Atomic Notes/Example.md" --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --collector-input /tmp/networked-thinking-audit/example-audit.jsonl
python3 scripts/collect_model_judgments.py --runner codex --vault /path/to/vault --audit-jsonl /tmp/networked-thinking-audit/example-audit.jsonl --output-jsonl /tmp/networked-thinking-audit/example-judgment.jsonl --raw-dir /tmp/networked-thinking-model-raw/example --model gpt-5.5
python3 scripts/apply_model_judgments.py --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json --model-judgments /tmp/networked-thinking-audit/example-judgment.jsonl --output-jsonl /tmp/networked-thinking-audit/example-applied.jsonl --output-manifest /tmp/networked-thinking-audit/example-applied-manifest.json --allow-missing
```

The preparation step validates the deterministic audit rows and writes only the
selected row. The collector adds stored schema and prompt provenance.

## Collect a batch

For exhaustive runs, use the validated batch collector with a selected local
agent runner. To use Codex CLI:

```bash
python3 scripts/collect_model_judgments.py --runner codex --vault /path/to/vault --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --output-jsonl /tmp/networked-thinking-audit/model-judgments.jsonl --raw-dir /tmp/networked-thinking-model-raw --model gpt-5.5
```

For local agent CLIs that accept the prompt on stdin and write the final response
to stdout or a file, use the generic command runner:

```bash
python3 scripts/collect_model_judgments.py --runner command --command 'local-agent --write-final-response "{output_path}"' --vault /path/to/vault --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --output-jsonl /tmp/networked-thinking-audit/model-judgments.jsonl --raw-dir /tmp/networked-thinking-model-raw
```

The command runner sends the prompt on stdin. If the command writes the final
JSONL response to stdout, stdout is parsed. If it writes to `{output_path}`, that
file is parsed instead. Quote path placeholders such as `{output_path}`,
`{stdout_path}`, and `{stderr_path}` in command templates when paths may contain
spaces. Use doubled braces for literal `{` or `}` characters.

Keep `--raw-dir` outside the vault by default because it contains private note
content in prompts and logs. The collector stamps each stored judgment with the
matching audit row's `prompt_version`. It resumes only when existing provenance
matches, validates each response, and splits failed batches into smaller retries.

## Apply judgments

The collector stores model responses as JSONL, one strict
`schemas/model-judgment.schema.json` object per line. Then apply them to
the deterministic audit rows before generating the model-judgment report or
Base:

```bash
python3 scripts/apply_model_judgments.py --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json --model-judgments /tmp/networked-thinking-audit/model-judgments.jsonl --output-jsonl /tmp/networked-thinking-audit/model-applied.jsonl --output-manifest /tmp/networked-thinking-audit/model-applied-manifest.json
```

By default, the apply step fails unless every audit row has exactly one
matching model judgment. Use `--allow-missing` only for a deliberate sampling
pass; unmatched rows stay `pending_model: true`. Supplied judgments with missing
or mismatched `prompt_version` provenance are rejected.

For reviewed rows, model findings replace deterministic semantic findings. The
apply step keeps only deterministic audit checks a single-note model cannot
reliably infer: `missing_frontmatter`, `missing_parent`, `malformed_anki`,
`duplicate_overlap`, `dae_sentence_case`, and `decayed_latex_command`.
These checks read exact file characters, structure, markers, or surrounding
vault content.
