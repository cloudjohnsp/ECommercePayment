#!/usr/bin/env bash
set -euo pipefail

python_bin=python
skip_install=false
skip_image=false

usage() {
  echo "Usage: $0 [--python PATH] [--skip-install] [--skip-image]" >&2
}

while (($#)); do
  case "$1" in
    --python) python_bin="$2"; shift 2 ;;
    --skip-install) skip_install=true; shift ;;
    --skip-image) skip_image=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd -- "$script_dir/.." && pwd)"

if [[ "$python_bin" != */* && "$python_bin" != *\\* ]]; then
  command -v "$python_bin" >/dev/null 2>&1 || {
    echo "Python executable '$python_bin' was not found." >&2
    exit 1
  }
elif [[ ! -x "$python_bin" ]]; then
  echo "Python executable '$python_bin' was not found or is not executable." >&2
  exit 1
fi

if [[ "$skip_image" == false ]]; then
  if command -v docker >/dev/null 2>&1; then
    docker_bin=docker
  elif command -v docker.exe >/dev/null 2>&1; then
    docker_bin=docker.exe
  else
    echo "Docker was not found. Install or start Docker Desktop and try again." >&2
    exit 1
  fi
fi

invoke_python() {
  "$python_bin" "$@"
}

cd "$root"
if [[ "$skip_install" == false ]]; then
  invoke_python -m pip install --requirement requirements-dev.txt
fi
invoke_python -m pip check
invoke_python -m ruff check .
invoke_python -m compileall -q app tests wsgi.py
invoke_python -m pytest

if [[ "$skip_image" == false ]]; then
  revision="$(git rev-parse HEAD)"
  tag="ecommerce-payment:sha-$revision"
  [[ -z "$(git status --porcelain)" ]] || tag+="-dirty"
  "$docker_bin" build --label "org.opencontainers.image.revision=$revision" --tag "$tag" .
fi

echo "Payment local gate passed."
