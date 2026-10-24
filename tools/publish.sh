#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Run only in an authenticated environment, after reviewing the source.
command -v gh >/dev/null
if [ ! -d .git ]; then
 git init -b main
 git add .
 git -c user.name='Codex' -c user.email='codex@openai.com' commit -m 'Jerzy Audio Platform: development version and verified cloud artifacts'
fi
gh repo create jurekbak71-dev/JerzyAudioPlatform --private --source . --push
