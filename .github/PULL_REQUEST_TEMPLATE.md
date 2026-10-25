<!-- Tiny fix (< ~30 lines): the one-line why + linked issue is enough.
     Everything bigger needs How-tested with fail-before/pass-after evidence. -->
## What this PR does

<!-- One paragraph. Link the issue it resolves: -->

Closes #

## How tested

<!-- Commands + results. For behavior fixes: show it failing before and passing after. -->

## Checklist

- [ ] Linked issue exists (no drive-by features — file one first)
- [ ] Major change? Prior discussion or maintainer pre-approval linked above (undiscussed large PRs stall)
- [ ] Tests pass (`uv run pytest`) and lint is clean (`ruff check src tests`, `ruff format --check`)
- [ ] Dashboard touched? `biome` checks pass in `web_sota/`
- [ ] No stubs presented as implementations
- [ ] Diff is small and focused (one concern per PR)
- [ ] CHANGELOG updated (if the repo keeps one)

## Notes for the reviewer

<!-- Anything surprising, anything you deliberately did NOT do, manual gates still open. -->
