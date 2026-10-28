"""
Servicio de transcripción de voz (Whisper) para los bots.

POST /transcribe   cuerpo = audio crudo (ogg/opus de Telegram o Discord, mp3, wav, m4a...)
                   encabezado Authorization: Bearer <WHISPER_TOKEN>  (si WHISPER_TOKEN está definido)
                   respuesta: {"text": "...", "duration": 3.2}
GET  /health       {"ok": true, "model": "..."}

Variables de entorno:
    WHISPER_MODEL     tiny | base | small | medium (default: small)
    WHISPER_LANGUAGE  idioma fijo (default: es). Vacío = autodetectar
    WHISPER_THREADS   hilos de CPU (default: 4)
    WHISPER_TOKEN     clave compartida con los bots (recomendado)
    MAX_AUDIO_MB      tamaño máximo del audio (default: 10)
    MAX_AUDIO_SECONDS duración máxima (default: 120)
"""
from __future__ import annotations

import hmac
import io
import logging
import os
import threading

from flask import Flask, jsonify, request

MODEL_NAME = os.environ.get("WHISPER_MODEL", "small")
LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "es").strip() or None
THREADS = int(os.environ.get("WHISPER_THREADS", "4"))
TOKEN = os.environ.get("WHISPER_TOKEN", "").strip()
MAX_MB = float(os.environ.get("MAX_AUDIO_MB", "10"))
MAX_SECONDS = float(os.environ.get("MAX_AUDIO_SECONDS", "120"))
MODEL_DIR = os.environ.get("WHISPER_MODEL_DIR", "/models")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("whisper")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(MAX_MB * 1024 * 1024)

class AudioTooLong(Exception):
    pass


_model = None
_lock = threading.Lock()  # un audio a la vez: el modelo usa toda la CPU igual


def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        log.info("Cargando modelo '%s' (la primera vez se descarga)...", MODEL_NAME)
        _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8", cpu_threads=THREADS, download_root=MODEL_DIR)
        log.info("Modelo listo")
    return _model


def transcribe_bytes(data: bytes) -> tuple[str, float]:
    from faster_whisper.audio import decode_audio

    audio = decode_audio(io.BytesIO(data), sampling_rate=16000)
    duration = len(audio) / 16000
    if duration > MAX_SECONDS:
        raise AudioTooLong(f"El audio dura {duration:.0f}s; el máximo es {MAX_SECONDS:.0f}s.")
    model = get_model()
    with _lock:
        segments, _info = model.transcribe(
            audio, language=LANGUAGE, beam_size=5, vad_filter=True, condition_on_previous_text=False
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
    return text, duration


@app.get("/health")
def health():
    return jsonify({"ok": True, "model": MODEL_NAME})


@app.post("/transcribe")
def transcribe():
    if TOKEN:
        sent = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(sent, TOKEN):
            return jsonify({"error": "No autorizado."}), 401
    data = request.get_data()
    if not data:
        return jsonify({"error": "No llegó audio."}), 400
    try:
        text, duration = transcribe_bytes(data)
    except AudioTooLong as e:
        return jsonify({"error": str(e)}), 413
    except Exception:
        log.exception("Error transcribiendo")
        return jsonify({"error": "No pude procesar ese audio."}), 422
    return jsonify({"text": text, "duration": round(duration, 1)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
