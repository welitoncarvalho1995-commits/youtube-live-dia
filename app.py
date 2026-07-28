import os
import time
import subprocess
from flask import Flask, redirect, Response, request

app = Flask(__name__)

# ==========================================================
# CONFIGURACAO (voce pode mudar tudo por variaveis de ambiente
# no painel do Render, sem mexer no codigo)
# ==========================================================

# ID do video de live do YouTube.
# Ex: em https://www.youtube.com/watch?v=Df3g76Y25gs  o ID e "Df3g76Y25gs"
DEFAULT_ID = os.environ.get("YT_ID", "Df3g76Y25gs")

# Quanto tempo (em segundos) guardamos o link ja resolvido antes de
# pedir um novo ao YouTube. O link do YouTube costuma durar ~6h;
# usamos 3h (10800s) por seguranca.
CACHE_TTL = int(os.environ.get("CACHE_TTL", "10800"))

# (Opcional) Caminho de um arquivo de cookies do YouTube.
# Ajuda a evitar o bloqueio "confirme que voce nao e um robo".
# Veja o guia (secao "Se der erro de robo").
COOKIES_FILE = os.environ.get("COOKIES_FILE", "")

# Cache em memoria:  video_id -> (url_resolvida, expira_em)
_cache = {}


def resolver(video_id):
    """Devolve o link m3u8 atual do YouTube para o video_id dado."""
    agora = time.time()
    url, expira_em = _cache.get(video_id, (None, 0))
    if url and agora < expira_em:
        return url  # ainda valido, reutiliza

    cmd = ["yt-dlp", "-g", "-f", "best[protocol*=m3u8]/best"]
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        cmd += ["--cookies", COOKIES_FILE]
    cmd.append("https://www.youtube.com/watch?v=" + video_id)

    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return None

    linhas = out.stdout.strip().splitlines()
    if not linhas:
        return None

    resolvida = linhas[-1].strip()
    _cache[video_id] = (resolvida, agora + CACHE_TTL)
    return resolvida


@app.route("/")
def home():
    # Usado pelo Render para checar se o app esta de pe.
    return "OK"


@app.route("/live")
def live():
    video_id = request.args.get("id", DEFAULT_ID)
    url = resolver(video_id)
    if not url:
        return Response("Nao consegui resolver o stream", status=502)
    return redirect(url, code=302)


if __name__ == "__main__":
    # Usado apenas quando voce roda localmente (python app.py).
    porta = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=porta)
