# Reuse library

Searches what is already built before building something new, so the same thing isn't paid for twice.

## Setup

1. Copy `reuse_sources.example.json` to `reuse_sources.json` and point it at your own code and template files.
2. Build the index:

```bash
python3 reuse_library.py index --sources reuse_sources.json
```

3. Search it before starting a new build; log what you reuse.

The search index (`index/`) is not shipped — it is derived data and rebuilds in one command.
