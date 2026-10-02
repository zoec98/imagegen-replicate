# fal.ai schema helper parsing fix

The Flux 3 text-to-image and edit-image model URLs were rejected without
`/api`. After adding it manually, both pages still failed endpoint extraction:
fal.ai now renders WebAPI JSON-LD in a script tag rather than the legacy meta
attribute. The embedded OpenAPI path and schema extraction still work.

Normalize model URLs to API documentation URLs and read both JSON-LD forms
with the standard HTML parser. Keep existing endpoint/schema and pricing logic.
Offline regressions cover both endpoint modes, URL variants, legacy metadata,
and malformed/unrelated JSON-LD. Public documentation fetches are manual
verification only; tests never call providers.
