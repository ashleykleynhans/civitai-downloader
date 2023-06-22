#!/usr/bin/env bash
URL=${1}
USER_AGENT_STRING="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

echo "Downloading model from ${URL}, please wait..."

curl -JsL --remote-name -A "${USER_AGENT_STRING}" "${URL}"
