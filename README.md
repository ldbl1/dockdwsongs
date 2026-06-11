# dwSongs Docker Edition

Aplicación web Dockerizada para descargar audio/vídeo desde YouTube, editar metadatos, gestionar carátulas y organizar archivos en una estructura compatible con Jellyfin.

## Características

- Descarga desde YouTube usando yt-dlp.
- Conversión mediante FFmpeg.
- Soporte audio: MP3, FLAC, M4A.
- Soporte vídeo: MP4, MKV.
- Edición de metadatos.
- Carátulas automáticas usando MusicBrainz / Cover Art Archive.
- Subida manual de carátula.
- Organización compatible con Jellyfin.
- Refresco automático opcional de Jellyfin.
- SQLite persistente.
- Docker-first.

## Estructura Jellyfin

Audio:

```text
Music/{Artist}/{Album} ({Year})/{TrackNumber} - {Title}.{ext}
