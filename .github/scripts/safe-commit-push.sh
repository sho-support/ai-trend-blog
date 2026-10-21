#!/usr/bin/env bash
# Safely publish generated files from GitHub Actions without force-pushing.
set -euo pipefail

commit_message="${1:?A commit message is required}"

git config user.name "${GIT_BOT_NAME:-AI Article Bot}"
git config user.email "actions@github.com"

git add -A
if git diff --cached --quiet; then
  echo "No generated changes to commit."
  exit 0
fi

git commit -m "$commit_message"

# Other scheduled workflows can update main while this job is generating.
# Rebase on the current remote state and retry if another push wins the race.
for attempt in 1 2 3 4 5; do
  echo "Safe publish attempt ${attempt}/5"
  git fetch --no-tags origin main

  if ! git -c rerere.enabled=false rebase origin/main; then
    echo "::error::Generated changes conflict with newer main. Refusing to overwrite or force-push."
    git rebase --abort || true
    exit 1
  fi

  if git push origin HEAD:main; then
    echo "Generated files published successfully."
    exit 0
  fi

  echo "Remote main changed during push; retrying."
  sleep "$((attempt * 2))"
done

echo "::error::Could not safely publish generated files after 5 attempts."
exit 1
