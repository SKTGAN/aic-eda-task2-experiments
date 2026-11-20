#!/usr/bin/env bash
set -Eeuo pipefail
umask 022
[[ $(id -u) == 0 ]] || { echo "Run as root on the new Ubuntu host." >&2; exit 1; }
if [[ -f /etc/os-release ]]; then . /etc/os-release; fi
[[ ${ID:-} == ubuntu && -n ${VERSION_CODENAME:-} ]] || { echo "Expected Ubuntu." >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt=(apt-get -o Acquire::Retries=1 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20)

"${apt[@]}" update
"${apt[@]}" install -y --no-install-recommends ca-certificates curl gnupg python3-yaml
install -m 0755 -d /etc/apt/keyrings
if ! command -v docker >/dev/null; then
  curl -fSL --connect-timeout 10 --max-time 40 https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $VERSION_CODENAME
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
fi
if ! command -v nvidia-ctk >/dev/null; then
  curl -fsSL --connect-timeout 10 --max-time 40 https://nvidia.github.io/libnvidia-container/gpgkey |
    gpg --batch --yes --dearmor -o /etc/apt/keyrings/nvidia-container-toolkit.gpg
  curl -fsSL --connect-timeout 10 --max-time 40 https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |
    sed 's#deb https://#deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit.gpg] https://#' > /etc/apt/sources.list.d/nvidia-container-toolkit.list
fi
"${apt[@]}" update
packages=()
if ! command -v docker >/dev/null; then packages+=(docker-ce docker-ce-cli containerd.io); fi
if ! command -v nvidia-ctk >/dev/null; then packages+=(nvidia-container-toolkit); fi
if (("${#packages[@]}")); then "${apt[@]}" install -y --no-install-recommends "${packages[@]}"; fi
nvidia-ctk runtime configure --runtime=docker
systemctl enable --now docker
systemctl restart docker
docker info --format '{{.ServerVersion}} {{.Runtimes}}'
python3 -c 'import yaml; print(yaml.__version__)'
