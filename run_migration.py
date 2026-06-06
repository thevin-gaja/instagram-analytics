#!/usr/bin/env python3
import json, pathlib
from bot.migrate import migrate

cache_file = pathlib.Path("metrics_cache.json")
cache = json.loads(cache_file.read_text())
migrated = migrate(cache)
cache_file.write_text(json.dumps(migrated, indent=2))
print(f"Migrated {len(migrated)} videos.")
