# Wiro model parity research

## Epic

Research whether image models already configured for Replicate or fal.ai are
also available through Wiro. For each confirmed Wiro model, capture Wiro's own
provider contract and add a provider-scoped entry to the Wiro registry.

The current Wiro entries, `seedream5-pro-uncensored` and
`seedream5-lite-uncensored`, already cover their model families. Other Wiro
variants of those models are reported but are not automatically added.

## User story

As an `imagegen` operator, I want models that I already use through Replicate
or fal.ai to be available through Wiro when Wiro actually offers them, so I can
choose the provider without losing registry-driven validation, editing, cost,
or metadata behavior.

## Research inventory

The Replicate registry currently has 14 selectable entries and the fal.ai
registry has 21. The table groups their 35 entries into 28 apparent model
families for research. Grouping is only a search aid; it does not assert that
similarly named provider endpoints have identical contracts.

| Model | Existing registry entries | Interest |
| --- | --- | --- |
| Bria Fibo | `falai:bria-fibo` | Skip |
| Ernie Image | `falai:ernie-image` | Skip |
| Ernie Image Turbo | `falai:ernie-image-turbo` | Skip |
| Flux 2 | `falai:flux-2` | Research |
| Flux 2 Flex | `replicate:flux-flex` | Research |
| Flux 2 Pro | `falai:flux-2-pro` | Skip |
| Flux 2 Realism | `falai:flux-2-realism` | Research |
| GPT Image 1.5 | `replicate:gpt-image-15`, `falai:gpt-image15` | Research |
| GPT Image 2 | `replicate:gpt-image-2`, `falai:gpt-image-2` | Research |
| Grok Imagine Image | `replicate:grok-imagine`, `falai:grok` | Research |
| HiDream I1 Dev | `falai:hidream-dev` | Research |
| HiDream I1 Fast | `falai:hidream-fast` | Research |
| HiDream I1 Full | `falai:hidream-full` | Skip |
| Imagen 4 | `replicate:imagen-4` | Research |
| Imagen 4 Fast | `replicate:imagen-4-fast` | Research |
| Imagen 4 Ultra | `replicate:imagen-4-ultra` | Research |
| Krea 2 Large | `falai:krea-2-large` | Research |
| Krea 2 Medium | `falai:krea-2-medium` | Research |
| Krea 2 Turbo | `falai:krea-2-turbo` | Research |
| Nano Banana 2 | `replicate:nano-banana-2`, `falai:nano-banana-2` | Research |
| Nano Banana Pro | `replicate:nano-banana-pro` | Research |
| Qwen Image 2512 | `replicate:qwen-2512` | Skip |
| Seedream 4 | `falai:seedream` | Skip |
| Seedream 4.5 | `replicate:seedream45`, `falai:seedream45` | Research |
| Seedream 5 Lite | `replicate:seedream5`, `falai:seedream5` | Already covered |
| Seedream 5 Pro | `replicate:seedream5-pro`, `falai:seedream5-pro` | Already covered |
| Wan 2.7 Image Pro | `replicate:wan-27-pro` | Research |
| Z-Image Turbo | `falai:zit` | Research |

## Acceptance criteria

- The Interest column is authoritative: `Research` rows are investigated,
  `Skip` rows require no Wiro research or implementation, and `Already covered`
  rows require only a report of alternate Wiro variants.
- Every `Research` row receives a recorded Wiro status: available, unavailable,
  ambiguous, or blocked from verification.
- If Wiro offers both normal and uncensored endpoints for a researched model,
  add the uncensored endpoint and report the normal endpoint. If Wiro offers
  only a normal endpoint, it may be added.
- More or alternate Wiro versions of an inventory model are reported. Versions
  outside the inventory are not automatically added.
- Availability is confirmed from Wiro's current catalog and authenticated Tool
  Detail response. A matching display name or common upstream vendor alone is
  not sufficient evidence.
- An available model records its exact Wiro `owner/model` identity,
  documentation/runtime URLs, text and edit capabilities, parameter names,
  types, defaults, choices, bounds, fixed inputs, source-image limits, output
  shape, expected runtime, and provider-reported pricing.
- Wiro-specific safety controls or endpoint variants are recorded exactly as
  supplied. No safety flag, tolerance, or uncensored behavior is inferred from
  another provider's contract.
- Each confirmed model receives a unique provider-scoped alias and selectable
  display name in the Wiro registry. Existing Replicate, fal.ai, and Wiro
  entries remain unchanged.
- Registry-driven web and CLI discovery, validation, text generation, editing
  where supported, history, and embedded metadata recognize each added Wiro
  entry through the existing provider boundaries.
- Automated tests use sanitized provider responses and fake HTTP transports;
  they never submit billable Wiro generations.
- Schema discovery may use the authenticated, non-generating Tool Detail API.
  Any paid generation probe requires separate explicit authorization and is
  limited to unresolved response or upload behavior.

## Out of scope

- Adding models that are not already represented in the Replicate or fal.ai
  registries.
- Treating approximate, renamed, versionless, or vendor-adjacent Wiro tools as
  matches without documented evidence.
- Refactoring provider abstractions or changing existing model aliases while
  performing the survey.
