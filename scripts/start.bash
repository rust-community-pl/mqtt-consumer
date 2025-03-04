#!/usr/bin/env /bin/bash
set -Eeuxo pipefail

: Running migrations \
&& alembic upgrade head \
&& : Running the consumer \
&& python -m consumer "${1:-consume}" \
&& : Finished