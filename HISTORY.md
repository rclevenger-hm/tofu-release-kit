# Commit history provenance

The initial implementation was developed in October 2026. Its initial commits use
synthetic author and committer dates distributed across January–September 2026,
at the repository owner's request. These dates organize the initial import;
they do not represent development, testing, releases, or production use on those dates.

Release dates and validation results should be read from release records and CI runs,
not inferred from the synthetic initial commit timestamps. Subsequent maintenance
should use its actual development dates.

## Importing the dated history

The publishing connector cannot set Git author/committer timestamps. The initial
source snapshot is therefore published using real connector timestamps, with the
dated local history preserved in `history/initial-import.bundle` and its checksum
in `history/import.json`.

From a clean authenticated clone on `main`, run:

```sh
python scripts/import_history.py --push
```

The script verifies the bundle, fast-forwards to origin/main, imports the history
on an `initial-import` branch, and merges that history while preserving the current
main tree. It uses a normal push with no force and does not rewrite existing remote
commits. Git name/email must already be configured. Review the script before use.

Until this step is performed, the dated commits are inside the bundle and do not
appear in GitHub's default-branch commit history. Contribution-calendar attribution
also depends on GitHub's email and repository eligibility rules.
