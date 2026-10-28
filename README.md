# Servicio Whisper (transcripcion de voz para los bots)

Contenedor que transcribe audios a texto en espanol, localmente (faster-whisper, CPU). Lo usan los bots de Telegram/Discord de los otros sitios para busquedas por voz. No envia audio a ningun servicio externo.

## Instalar en Portainer

1. Subir esta carpeta a un repositorio privado de GitHub (o a una carpeta del servidor): `Dockerfile`, `docker-compose.yml`, `app.py`, `requirements.txt`.
2. Crear un Stack nuevo desde ese repositorio y definir las variables:
   - `WHISPER_TOKEN` (obligatoria): clave larga al azar. La misma se carga luego en los bots.
   - `WHISPER_MODEL` (opcional): `tiny`, `base`, `small` (default) o `medium`. Mas grande = mas preciso y mas lento. Si el servidor es modesto, empezar con `base`.
   - `WHISPER_THREADS` (opcional, default 4): hilos de CPU.
3. Desplegar. La primera vez descarga el modelo al volumen `whisper_models` (cientos de MB, mas grande cuanto mas grande el modelo); el primer audio puede tardar por eso. Ver el progreso en los logs del contenedor.
4. Probar: `http://IP-DEL-SERVIDOR:9000/health` debe responder `{"ok": true, ...}`.

## Conectarlo a los bots

En el stack de cada sitio (Zoologic, Archivo IT) agregar:

- `WHISPER_URL` = `http://IP-DEL-SERVIDOR:9000` (usar la IP del servidor, no `localhost`: son stacks distintos)
- `WHISPER_TOKEN` = la misma clave

y redesplegar.

## Seguridad

- No expongas el puerto 9000 a Internet. Solo red local. El token evita usos no autorizados dentro de la red.
- Los audios se procesan en memoria y no se guardan.
- Limites: 10 MB y 120 s por audio (`MAX_AUDIO_SECONDS`); los bots ademas limitan a 60 s.
