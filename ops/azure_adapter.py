"""Adaptateur Azure — NON fourni par le brief, ajouté pour ce poste de travail.

`ops/drift_proxy.py` [FOURNI] appelle toujours l'amont avec `?api-version=...`
et l'application envoie `max_tokens`. Le modèle déployé sur cette ressource
Azure (endpoint `/openai/v1`, nouvelle API unifiée) refuse les deux :
« API version not supported » et « Unsupported parameter: 'max_tokens' ».

Plutôt que de modifier `ops/drift_proxy.py` ou `app/llm_client.py` (fournis),
cet adaptateur se place entre le proxy et le vrai endpoint Azure : il retire
`api-version` et renomme `max_tokens` en `max_completion_tokens` avant de
relayer.

    AZURE_AI_REAL_ENDPOINT   le vrai endpoint Azure (…/openai/v1)
    AZURE_AI_ADAPTER_PORT    port d'écoute (défaut 9000)
"""
from __future__ import annotations

import json
import os

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response

app = FastAPI(title="Azure adapter")


@app.api_route("/{chemin:path}", methods=["GET", "POST"])
async def relayer(chemin: str, request: Request) -> Response:
    base = os.environ.get("AZURE_AI_REAL_ENDPOINT", "").rstrip("/")
    url = f"{base}/{chemin}"  # api-version ignorée : l'API /openai/v1 n'en veut pas

    corps = await request.body()
    if corps:
        try:
            data = json.loads(corps)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and "max_tokens" in data:
            data["max_completion_tokens"] = data.pop("max_tokens")
            corps = json.dumps(data, ensure_ascii=False).encode("utf-8")

    entetes = {
        k: v
        for k, v in request.headers.items()
        if k.lower() in {"content-type", "api-key", "authorization", "accept"}
    }
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.request(request.method, url, content=corps, headers=entetes)
    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "application/json"),
    )


def main() -> int:
    port = int(os.environ.get("AZURE_AI_ADAPTER_PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
