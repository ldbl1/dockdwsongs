# Changelog

Todos los cambios relevantes de este proyecto se documentarán en este fichero.

El formato está inspirado en [Keep a Changelog](https://keepachangelog.com/), aunque el proyecto todavía no usa versionado formal estricto.

---

## [Unreleased]

### Pendiente / ideas futuras

- Selector manual de release de MusicBrainz para elegir álbum, edición y número de pista cuando haya múltiples coincidencias.
- Edición de idiomas desde panel admin.
- Migraciones de base de datos para evitar borrar `data/dwsongs.db` al cambiar modelos.
- Mejoras visuales adicionales en filtros y tablas.
- Exportación de histórico admin a CSV/XLSX.
- Mejor gestión de errores por canción en acciones masivas.

---

## [1.5.0] - 2026-06-12

### Added

- Sistema de usuarios con login y sesiones.
- Pantalla de primer arranque `/setup` para crear el primer usuario administrador.
- Panel de administración de usuarios en `/admin/users`.
- Histórico admin global en `/admin/downloads`.
- Auditoría básica de acciones por descarga.
- Asociación de descargas a usuario.
- Visibilidad por rol:
  - usuarios normales ven sus descargas,
  - usuarios admin ven todo el histórico.
- Comando de consola `python -m app.manage` para:
  - listar usuarios,
  - crear usuarios,
  - resetear contraseñas,
  - activar/desactivar usuarios,
  - conceder/quitar permisos admin.
- Filtros y selector de columnas en histórico admin.
- Filtros y selector de columnas en histórico principal.
- Acciones en bloque para:
  - guardar seleccionados,
  - buscar datos seleccionados,
  - descargar seleccionados,
  - enviar seleccionados a Jellyfin,
  - eliminar seleccionados.
- Bloqueo de acciones en la lista de URLs mientras se obtiene el nombre del vídeo.
- Timeout de 5 segundos al obtener nombre de vídeo.
- Estado “No encontrado” con edición manual si no se obtiene nombre automáticamente.
- Botón “Enviar a Jellyfin” deshabilitado si el fichero todavía no está descargado.
- Envío masivo a Jellyfin omitiendo registros no descargados y mostrando resumen.
- Idiomas externos mediante ficheros JSON en `app/i18n/`.
- Fichero `.env.example` para configuración segura.
- Fichero `.gitignore` para evitar subir datos, descargas, configuración privada y bases de datos.

### Changed

- La pantalla principal se reorganiza con tabla de URLs y acciones por fila.
- El histórico permite edición inline de metadatos.
- El flujo de envío a Jellyfin elimina el fichero temporal de `incoming` tras copiar correctamente a biblioteca.
- El botón eliminar ya no borra el fichero final de Jellyfin.
- La pantalla de ajustes separa “Guardar ajustes” y “Probar conexión”.
- “Probar conexión” ya no cambia idioma ni guarda otros ajustes.
- Mejoras visuales en Settings, Login, Setup y Admin.
- Búsqueda de metadatos mejorada con lookup profundo de MusicBrainz para intentar recuperar número de pista y disco.

### Fixed

- Corrección de duplicados en `incoming` tras enviar a Jellyfin.
- Corrección de eliminación accidental del fichero final en biblioteca Jellyfin.
- Corrección de errores de plantillas Jinja por etiquetas HTML incompletas.
- Corrección de errores de sintaxis en `security.py` y `auth.py` generados durante iteraciones previas.
- Corrección de cambio de idioma al pulsar “Probar conexión”.
- Corrección de acciones disponibles mientras una URL todavía está obteniendo información.

---

## [1.0.0] - 2026-06-11

### Added

- Primera versión funcional de dwSongs Docker Edition.
- Descarga de audio desde YouTube.
- Cola e histórico básico.
- Edición básica de metadatos.
- Envío a biblioteca de Jellyfin.
- Integración inicial con Jellyfin mediante API Key.
- Organización de música en estructura compatible con Jellyfin.
- Soporte inicial para Settings.
- Soporte inicial para español e inglés.
