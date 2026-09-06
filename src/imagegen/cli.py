"""Command-line entry point for imagegen."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from imagegen.model_registry import (
    GenerationTarget,
    ModelParameter,
    ProviderId,
    ProviderModel,
    RegistryLookupError,
    list_models_for_provider,
    list_providers,
    resolve_generation_target,
    resolve_model_ref,
)


@dataclass(frozen=True)
class CliRequest:
    provider: ProviderId
    model: ProviderModel
    target: GenerationTarget
    prompt: str
    parameters: dict[str, object]
    quiet: bool


class CliArgumentError(ValueError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(option in arguments for option in ("--help", "-h")):
        bootstrap = _bootstrap_parser()
        try:
            selected, _ = bootstrap.parse_known_args(arguments)
        except SystemExit as error:
            return int(error.code or 0)
        if selected.provider and selected.model:
            return _model_help(arguments, selected.provider, selected.model)
        parser = _global_parser()
        try:
            parser.parse_args(arguments)
        except SystemExit as error:
            return int(error.code or 0)

    try:
        request = parse_cli_request(arguments)
    except CliArgumentError as error:
        print(f"imagegen: error: {error}", file=sys.stderr)
        return 2
    if isinstance(request, int):
        return request
    print(
        "imagegen: error: generation arguments are not implemented yet", file=sys.stderr
    )
    return 1


def parse_cli_request(arguments: Sequence[str]) -> CliRequest | int:
    bootstrap = _bootstrap_parser()
    try:
        selected, _ = bootstrap.parse_known_args(arguments)
    except SystemExit as error:
        return int(error.code or 0)
    if not selected.provider:
        raise CliArgumentError("--provider is required for generation.")
    if not selected.model:
        raise CliArgumentError("--model is required for generation.")
    try:
        model = resolve_model_ref(selected.model, selected_provider=selected.provider)
        target = resolve_generation_target(
            selected.provider,
            model.alias,
            edit_mode=False,
        )
    except RegistryLookupError as error:
        raise CliArgumentError(str(error)) from error
    parser = _model_parser(selected.provider, model, target)
    try:
        parsed = parser.parse_args(arguments)
    except SystemExit as error:
        return int(error.code or 0)
    if parsed.prompt is None and parsed.file is None:
        raise CliArgumentError("exactly one of --prompt or --file is required.")
    prompt = parsed.prompt
    if parsed.file is not None:
        try:
            prompt = Path(parsed.file).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise CliArgumentError(
                f"could not read prompt file `{parsed.file}`: {error}"
            ) from error
    prompt = prompt.strip()
    if not prompt:
        raise CliArgumentError("prompt must not be empty.")
    parameters = {
        parameter.name: getattr(parsed, parameter.name)
        for parameter in target.parameters
        if parameter.name not in {"prompt", _source_parameter(model)}
        and parameter.name not in target.fixed_inputs
        and getattr(parsed, parameter.name, None) is not None
    }
    return CliRequest(
        provider=selected.provider,
        model=model,
        target=target,
        prompt=prompt,
        parameters=parameters,
        quiet=parsed.quiet,
    )


def _bootstrap_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--provider")
    parser.add_argument("--model")
    return parser


def _model_help(arguments: list[str], provider: str, model_ref: str) -> int:
    try:
        model = resolve_model_ref(model_ref, selected_provider=provider)
        target = resolve_generation_target(provider, model.alias, edit_mode=False)
    except RegistryLookupError as error:
        print(f"imagegen: error: {error}", file=sys.stderr)
        return 2

    parser = _model_parser(provider, model, target)
    try:
        parser.parse_args(arguments)
    except SystemExit as error:
        return int(error.code or 0)
    parser.error("generation arguments are not implemented yet")
    return 2


def _source_parameter(model: ProviderModel) -> str | None:
    if model.edit_target is None or model.edit_target.source_images is None:
        return None
    return model.edit_target.source_images.provider_field


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


def _model_parser(
    provider: str,
    model: ProviderModel,
    target: GenerationTarget,
) -> argparse.ArgumentParser:
    model_alias = model.alias
    parser = argparse.ArgumentParser(
        prog="imagegen",
        description=(
            f"Generate with {provider} model {target.display_name} "
            f"(alias: {model_alias})."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--provider", default=provider, help=argparse.SUPPRESS)
    parser.add_argument("--model", default=model_alias, help=argparse.SUPPRESS)
    prompt = parser.add_mutually_exclusive_group()
    prompt.add_argument("--prompt", metavar="TEXT")
    prompt.add_argument("--file", metavar="FILENAME")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only generated image paths on success",
    )
    source_parameter = _source_parameter(model)
    for parameter in target.parameters:
        if (
            parameter.name in {"prompt", source_parameter}
            or parameter.name in target.fixed_inputs
        ):
            continue
        _add_parameter_option(parser, parameter)
    return parser


def _add_parameter_option(
    parser: argparse.ArgumentParser,
    parameter: ModelParameter,
) -> None:
    option_names = [f"--{parameter.name}"]
    hyphenated = f"--{parameter.name.replace('_', '-')}"
    if hyphenated not in option_names:
        option_names.append(hyphenated)
    help_text = parameter.description
    if parameter.default not in ("", ()):
        help_text += f" (default: {parameter.default})"
    if parameter.choices:
        help_text += f" (choices: {', '.join(map(str, parameter.choices))})"
    if parameter.minimum is not None or parameter.maximum is not None:
        help_text += f" (range: {parameter.minimum!s} to {parameter.maximum!s})"
    kwargs = {"default": None, "help": help_text}
    if parameter.type == "boolean":
        kwargs["action"] = argparse.BooleanOptionalAction
    else:
        kwargs["type"] = {
            "integer": int,
            "number": float,
            "select": str,
            "string": str,
        }.get(parameter.type)
        if parameter.choices:
            kwargs["choices"] = parameter.choices
    parser.add_argument(*option_names, **kwargs)


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
