#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$ROOT_DIR/electron/linux-runtime"
# Read the same immutable versions used by the desktop installer.
readarray -t RUNTIME_PINS < <(python3 - "$ROOT_DIR/app/services/runtime_versions.json" <<'PINS'
import json
import sys
with open(sys.argv[1]) as source:
    manifest = json.load(source)
print(manifest["llama.cpp"]["commit"])
print(manifest["llama-swap"]["version"].removeprefix("v"))
print(manifest["llama-swap"]["assets"]["Linux-x86_64"]["sha256"])
PINS
)
LLAMA_COMMIT="${RUNTIME_PINS[0]}"
SWAP_VERSION="${RUNTIME_PINS[1]}"
SWAP_SHA256="${RUNTIME_PINS[2]}"

[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
for command in git cmake make cc c++ curl sha256sum tar; do
  command -v "$command" >/dev/null || { echo "Missing Linux build tool: $command" >&2; exit 1; }
done
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

# Build on the supported glibc baseline, without host-specific CPU instructions.
git init -q "$BUILD_DIR/source"
git -C "$BUILD_DIR/source" remote add origin https://github.com/ggml-org/llama.cpp.git
git -C "$BUILD_DIR/source" fetch --depth 1 origin "$LLAMA_COMMIT"
git -C "$BUILD_DIR/source" checkout --detach FETCH_HEAD
cmake -S "$BUILD_DIR/source" -B "$BUILD_DIR/build" \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DLLAMA_OPENSSL=OFF \
  -DGGML_SSE42=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF \
  -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON
cmake --build "$BUILD_DIR/build" --target llama-server --parallel "${CMAKE_BUILD_PARALLEL_LEVEL:-2}"

curl --fail --location --retry 3 \
  "https://github.com/mostlygeek/llama-swap/releases/download/v${SWAP_VERSION}/llama-swap_${SWAP_VERSION}_linux_amd64.tar.gz" \
  -o "$BUILD_DIR/swap.tar.gz"
echo "$SWAP_SHA256  $BUILD_DIR/swap.tar.gz" | sha256sum --check
mkdir -p "$BUILD_DIR/swap"
tar -xzf "$BUILD_DIR/swap.tar.gz" -C "$BUILD_DIR/swap"

mkdir -p "$OUTPUT_DIR"
cp "$ROOT_DIR/app/services/runtime_versions.json" "$OUTPUT_DIR/runtime-versions.json"
install -m 755 "$BUILD_DIR/build/bin/llama-server" "$OUTPUT_DIR/llama-server"
install -m 755 "$BUILD_DIR/swap/llama-swap" "$OUTPUT_DIR/llama-swap"
cp "$BUILD_DIR/source/LICENSE" "$OUTPUT_DIR/llama.cpp-LICENSE"
cp "$BUILD_DIR/swap/LICENSE.md" "$OUTPUT_DIR/llama-swap-LICENSE.md"
"$OUTPUT_DIR/llama-server" --version
"$OUTPUT_DIR/llama-swap" --version
