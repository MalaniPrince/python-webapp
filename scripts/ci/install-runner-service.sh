#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run this installer with sudo.' >&2; exit 1; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runner_dir=/home/priyanshu/actions-runner-day2
test -f "$runner_dir/.runner"
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
./svc.sh start
./svc.sh status
