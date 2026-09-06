"""Command-line entry point for imagegen."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from imagegen.model_registry import list_models_for_provider, list_providers


def main(argv: Sequence[str] | None = None) -> int:
    parser = _global_parser()
    try:
        parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)
    parser.error("generation arguments are not implemented yet")
    return 2


def _global_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imagegen",
        description="Generate images through the configured imagegen providers.",
        epilog=_global_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--provider", metavar="PROVIDER")
    parser.add_argument("--model", metavar="MODEL")
    prompt = parser.add_mutually_exclusive_group()
    prompt.add_argument("--prompt", metavar="TEXT")
    prompt.add_argument("--file", metavar="FILENAME")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only generated image paths on success",
    )
    return parser


def _global_help_epilog() -> str:
    lines = ["Providers and models:"]
    for provider in list_providers():
        lines.append(f"  {provider.id} ({provider.display_name}):")
        for model in list_models_for_provider(provider.id):
            lines.append(f"    {model.alias} — {model.display_name}")
    lines.extend(
        (
            "",
            "Automation and agent usage:",
            "  1. Run `imagegen --help` to discover providers and models.",
            "  2. Run `imagegen --provider PROVIDER --model MODEL --help`.",
            "  3. Run generation with the discovered model options.",
            "  Use --quiet for one project-root-relative image path per line.",
            "  Errors go to stderr; exit 0 means success, 1 runtime failure,",
            "  and 2 argument or validation failure.",
            "",
            "Examples:",
            '  imagegen --provider replicate --model seedream45 --prompt "a red fox"',
            "  imagegen --provider falai --model seedream45 --file prompt.txt --quiet",
        )
    )
    return "\n".join(lines)
