"""Adapt the pinned upstream entry point for export-only checking."""
import json
from pathlib import Path

exporter = 'cacf989bd75f608700820f6afc595f32e7a99a4d'
manifest = json.loads(Path('lake-manifest.json').read_text())
assert len(manifest['packages']) == 1
assert manifest['packages'][0]['rev'] == exporter
manifest['packages'][0]['inputRev'] = exporter
Path('lake-manifest.json').write_text(json.dumps(manifest))
source = Path('Main.lean').read_text()
marker = '\ndef main (args : List String)'
assert source.count(marker) == 1
# Preserve upstream copyright and implementation; remove only its build launcher main.
Path('ComparatorDriver.lean').write_text(source.split(marker)[0])
p = Path('lakefile.toml')
text = p.read_text()
assert text.count('rev = "master"') == 1
text = text.replace('rev = "master"', 'rev = "' + exporter + '"')
p.write_text(text + '\n[[lean_lib]]\nname = "ComparatorDriver"\n\n[[lean_exe]]\nname = "gate-replay"\nroot = "GateReplay"\n')
