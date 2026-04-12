from __future__ import annotations

import argparse
import json
from pathlib import Path

from md2deck.config import AppConfig
from md2deck.pipeline import DeckPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md2deck",
        description="Generate a slide-master-aware PowerPoint deck from markdown.",
    )
    parser.add_argument("input_markdown", nargs="?", type=Path, help="Path to the source markdown file.")
    parser.add_argument("--master", dest="master_pptx", type=Path, help="Path to the slide master PPTX.")
    parser.add_argument("--output", dest="output_pptx", type=Path, help="Path for the generated PPTX.")
    parser.add_argument(
        "--batch-dir",
        dest="batch_dir",
        type=Path,
        help="Run the pipeline for every markdown file in a directory.",
    )
    parser.add_argument(
        "--masters-dir",
        dest="masters_dir",
        type=Path,
        help="Directory of master PPTX files used for batch mode or auto matching.",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        type=Path,
        help="Output directory for batch mode.",
    )
    parser.add_argument(
        "--working-dir",
        dest="working_dir",
        type=Path,
        default=Path.cwd(),
        help="Working directory for run artifacts.",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.batch_dir is not None:
        if not args.batch_dir.exists():
            raise FileNotFoundError(f"Batch directory not found: {args.batch_dir}")
        if args.masters_dir is None or not args.masters_dir.exists():
            raise FileNotFoundError("Batch mode requires --masters-dir with a valid directory.")
        if args.output_dir is None:
            raise ValueError("Batch mode requires --output-dir.")
        return

    if args.input_markdown is None:
        raise ValueError("Provide an input markdown file or use --batch-dir.")
    if not args.input_markdown.exists():
        raise FileNotFoundError(f"Markdown file not found: {args.input_markdown}")
    if args.input_markdown.suffix.lower() != ".md":
        raise ValueError(f"Expected a markdown input, got: {args.input_markdown}")
    if args.master_pptx is None or not args.master_pptx.exists():
        raise FileNotFoundError(f"Master deck not found: {args.master_pptx}")
    if args.master_pptx.suffix.lower() != ".pptx":
        raise ValueError(f"Expected a PPTX master, got: {args.master_pptx}")
    if args.output_pptx is None:
        raise ValueError("Single file mode requires --output.")


def run_single(input_markdown: Path, master_pptx: Path, output_pptx: Path, working_dir: Path) -> dict[str, str]:
    config = AppConfig(
        input_markdown=input_markdown.resolve(),
        master_pptx=master_pptx.resolve(),
        output_pptx=output_pptx.resolve(),
        working_dir=working_dir.resolve(),
    )
    pipeline = DeckPipeline(config)
    pipeline.run()
    print(f"Pipeline complete. Output deck: {config.output_pptx}")
    print(f"Run manifest: {config.output_pptx.with_suffix('.manifest.json')}")
    return {
        "input": str(config.input_markdown),
        "master": str(config.master_pptx),
        "output": str(config.output_pptx),
        "manifest": str(config.output_pptx.with_suffix(".manifest.json")),
    }


def run_batch(batch_dir: Path, masters_dir: Path, output_dir: Path, working_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    master_files = list(masters_dir.glob("*.pptx"))
    if not master_files:
        raise FileNotFoundError(f"No master PPTX files found in: {masters_dir}")

    results: list[dict[str, str]] = []
    for markdown_file in sorted(batch_dir.glob("*.md")):
        matched_master = resolve_master(markdown_file, master_files)
        output_file = output_dir / f"{markdown_file.stem}.pptx"
        results.append(run_single(markdown_file, matched_master, output_file, working_dir))

    report_path = output_dir / "batch-report.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Batch run complete. Report: {report_path}")
    return 0


def resolve_master(markdown_file: Path, master_files: list[Path]) -> Path:
    normalized_md = canonical_name(markdown_file.stem)
    scored = []
    for master in master_files:
        normalized_master = canonical_name(master.stem.replace("Template_", ""))
        score = overlap_score(normalized_md, normalized_master)
        scored.append((score, master))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def canonical_name(text: str) -> str:
    import re

    lowered = text.lower()
    lowered = re.sub(r"template_", "", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def overlap_score(left: str, right: str) -> int:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    return len(left_tokens & right_tokens)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)

    if args.batch_dir is not None:
        return run_batch(args.batch_dir.resolve(), args.masters_dir.resolve(), args.output_dir.resolve(), args.working_dir.resolve())

    run_single(args.input_markdown, args.master_pptx, args.output_pptx, args.working_dir)
    return 0
