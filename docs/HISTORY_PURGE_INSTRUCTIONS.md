# History Purge Instructions (PII / Debug Artifacts)

This repository previously tracked debug artifacts that may contain PII. New commits are cleaned and .gitignore prevents new artifacts. To fully remove them from history, rewrite the Git history.

Two supported methods are below. Coordinate with your team — a history rewrite requires force-push and developer resync.

## Option A: git-filter-repo (recommended)

1) Install

```
pipx install git-filter-repo  # or: brew install git-filter-repo
```

2) Review the list of paths/patterns to remove

- `sensitive-paths.txt` (in repo root) contains the exact patterns used for purge.

3) Dry-run preview (optional)

```
git filter-repo --path-glob-from-file sensitive-paths.txt --invert-paths --dry-run
```

4) Rewrite

```
# Make a backup clone first if needed
# Then run:
git filter-repo --path-glob-from-file sensitive-paths.txt --invert-paths
```

5) Force-push to remote

```
git push --force --all
git push --force --tags
```

6) Ask collaborators to re-clone or hard-reset onto new history.

## Option B: BFG Repo-Cleaner

1) Create a mirror clone

```
git clone --mirror <repo-url>
cd <repo>.git
```

2) Run BFG (download bfg.jar from the official site)

```
java -jar bfg.jar --delete-files ../sensitive-paths.txt .
```

3) Clean and push

```
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force --all
git push --force --tags
```

## Notes

- After rewriting, verify CI is green and that the removed files no longer appear in history.
- Keep `sensitive-paths.txt` updated alongside .gitignore if you introduce new debug patterns.
