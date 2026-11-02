#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run this installer with sudo.' >&2; exit 1; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runner_dir=/home/priyanshu/actions-runner-day2
test -f "$runner_dir/.runner"
# The listener needs ICU before it can read the runner's saved .env file.
# Install the Ubuntu 26.04 system package so service startup can load it.
if ! dpkg-query -W libicu78 >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends libicu78
fi
bash -n "$source_dir/daybook-load-image"
install -o root -g root -m 0755 "$source_dir/daybook-load-image" /usr/local/sbin/daybook-load-image
rule=$(mktemp)
trap 'rm -f -- "$rule"' EXIT
printf '%s\n' 'priyanshu ALL=(root) NOPASSWD: /usr/local/sbin/daybook-load-image' > "$rule"
visudo -cf "$rule"
install -o root -g root -m 0440 "$rule" /etc/sudoers.d/daybook-deploy
cd "$runner_dir"
if [[ ! -f .service ]]; then
  ./svc.sh install priyanshu
fi
./svc.sh stop
./svc.sh start
./svc.sh status
