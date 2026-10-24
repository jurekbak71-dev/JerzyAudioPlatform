#!/usr/bin/env python3
"""Preserve exit status and expose failures in GitHub annotations."""
import pathlib,subprocess,sys
path=pathlib.Path(sys.argv[1]);path.parent.mkdir(parents=True,exist_ok=True)
with path.open('w') as log:
 result=subprocess.run(sys.argv[2:],stdout=log,stderr=subprocess.STDOUT)
if result.returncode:
 tail=path.read_text(errors='replace')[-7000:]
 message=tail.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
 print('::error::'+message,flush=True)
else:print(path.read_text(errors='replace')[-2000:])
raise SystemExit(result.returncode)
