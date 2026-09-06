# AGENTS.md

## Git Tag Policy (AUDYT-112)

Before running `git push`, check if `CHANGELOG.md` was updated with a new version.
If a new version entry was added, tag the commit:

```bash
git tag -a v<version> -m "Release v<version>"
git push origin v<version>
```

Reference: `docs/Manifest/13-release-tagging.md`
