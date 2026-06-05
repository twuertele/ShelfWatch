# Release Checklist

ShelfWatch releases use semantic version tags such as `0.2.0`.

Before creating a GitHub release:

1. Update `version` in `custom_components/shelfwatch/manifest.json`.
2. Update `CHANGELOG.md`.
3. Run all unit tests in the development repository.
4. Run Home Assistant configuration validation.
5. Start the local Home Assistant test stack.
6. Verify setup, reauthentication, sensors, options, and Todo behavior.
7. Inspect Home Assistant logs for ShelfWatch errors.
8. Generate and validate the public HACS export.
9. Push the exported content to the public GitHub repository.
10. Wait for both GitHub validation workflows to pass.
11. Create a full GitHub release whose tag matches the manifest version.

Do not publish a tag without a GitHub release. HACS uses published releases
when determining available versions.
