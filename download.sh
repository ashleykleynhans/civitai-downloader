#!/usr/bin/env bash

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <URL> <DESTINATION>"
  echo "   eg: $0 https://civitai.com/api/download/models/15236 /workspace/stable-diffusion-webui/models/Stable-diffusion"
  exit 1
fi

URL=${1}
DESTINATION=${2}
USER_AGENT_STRING="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

if ! echo "${URL}" | grep -q "api"; then
  echo "ERROR: Incorrect URL provided, you must provide the Download link from CivitAI, not the link to the model page."
  exit 1
fi

echo "Downloading model from ${URL}, please wait..."

cd ${DESTINATION}

if ! curl -JsL --remote-name -A "${USER_AGENT_STRING}" "${URL}"; then
  echo "ERROR: curl command failed. Unable to download the file."
  exit 1
fi

echo "Model downloaded successfully!"
