#!/usr/bin/env bash
# Create the TrinoHub issue/label scheme in the repo. Idempotent (ignores "exists").
# Usage: REPO=owner/trinohub ./labels.sh
set -euo pipefail
REPO="${REPO:?Set REPO=owner/trinohub}"

create() { gh label create "$1" --repo "$REPO" --color "$2" --description "$3" --force; }

# Issue types (referenced by the issue-form templates)
create "bug"            "d73a4a" "Something is broken or behaves incorrectly"
create "enhancement"   "a2eeef" "New feature or improvement request"
create "question"      "d876e3" "A how-do-I / support question"
create "documentation" "0075ca" "Docs additions or fixes"
create "good first issue" "7057ff" "Good for newcomers"
create "help wanted"   "008672" "Extra attention is wanted"
create "needs-triage"  "ededed" "Not yet reviewed by a maintainer"

# Automation lifecycle (drives automation/run-agent.sh)
create "agent:queued"     "0e8a16" "Triaged & approved for the automated agent to work"
create "agent:in-review"  "fbca04" "Agent opened a draft PR; awaiting maintainer review"
create "agent:blocked"    "b60205" "Agent could not complete; needs human clarification"

echo "Labels ensured on $REPO."
