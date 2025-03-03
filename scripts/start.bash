#!/usr/bin/env /bin/bash
set -Eeuxo pipefail

: \
&& alembic upgrade head \
&& python -m consumer "${1:-consume}" \
&& :