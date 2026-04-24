#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y gcc

export PATH="$HOME/go/bin:$PATH"

CGO_ENABLED=1 go install -tags extended github.com/gohugoio/hugo@latest

hugo version
pip install -e .