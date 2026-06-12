# dwSongs

**dwSongs** es una aplicación web autoalojada para gestionar descargas de audio desde YouTube, editar metadatos musicales y organizar la música para Jellyfin.

Está pensada para ejecutarse en Docker y trabajar con una biblioteca musical compartida con Jellyfin.

---

## Características principales

- Descarga de audio desde URLs de YouTube.
- Cola de descargas con obtención automática de nombre original.
- Timeout de 5 segundos al obtener nombre de vídeo.
- Edición manual de metadatos si no se encuentra información.
- Edición de título, artista, álbum, año, pista y género.
- Búsqueda de metadatos con MusicBrainz.
- Organización automática en estructura compatible con Jellyfin.
- Envío a Jellyfin y refresco de biblioteca.
- Eliminación segura de ficheros temporales en `incoming` sin borrar la biblioteca final.
- Login de usuarios.
- Usuario administrador inicial desde `/setup`.
- Administración de usuarios.
- Reset de contraseñas desde interfaz admin y consola.
- Histórico admin global con datos de descargas, usuarios, fechas y acciones.
- Filtros y selector de columnas en histórico admin.
- Idiomas externos mediante ficheros JSON en `app/i18n/`.

---

## Estructura general

```text
app/
  auth.py
  config.py
  coverart.py
  database.py
  downloader.py
  i18n_loader.py
  jellyfin.py
  library.py
  main.py
  manage.py
  models.py
  security.py
  i18n/
    es.json
    en.json
  static/
    app.js
    css/
      app.css
  templates/
    admin_downloads.html
    admin_users.html
    base.html
    index.html
    login.html
    settings.html
    setup_admin.html
```

---

## Requisitos

- Docker
- Docker Compose
- Jellyfin, opcional pero recomendado
- Una carpeta compartida entre dwSongs y Jellyfin para la biblioteca musical

---

## Puesta en marcha rápida

1. Clona el repositorio:

```bash
git clone https://github.com/TU_USUARIO/dwsongs.git
cd dwsongs
```

2. Copia el fichero de entorno:

```bash
cp .env.example .env
```

3. Edita `.env` si quieres preconfigurar Jellyfin:

```env
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=tu_api_key
LIBRARY_MUSIC_PATH=/library/music
```

4. Levanta la aplicación:

```bash
docker compose up -d
```

5. Abre la aplicación:

```text
http://localhost:8080
```

6. En el primer arranque, crea el usuario administrador en:

```text
/setup
```

---

## Configuración de Jellyfin

En la pantalla **Ajustes** puedes configurar:

- URL de Jellyfin.
- API Key de Jellyfin.
- Ruta interna de biblioteca musical.
- Refresco automático de Jellyfin.
- Idioma de la interfaz.

Ejemplos de URL:

```text
http://jellyfin:8096
http://host.docker.internal:8096
http://192.168.1.50:8096
```

La ruta interna recomendada para dwSongs es:

```text
/library/music
```

Esa ruta debe apuntar mediante volumen Docker a la misma carpeta física que Jellyfin usa para su biblioteca musical.

---

## Organización de música

Cuando se envía una canción a Jellyfin, dwSongs organiza el fichero así:

```text
/library/music/Music/Artista/Álbum/01 - Título.mp3
```

Después de copiar el fichero a la biblioteca:

- se elimina el fichero temporal de `incoming`,
- no se borra el fichero final de Jellyfin,
- se registra la acción en el histórico.

---

## Usuarios y administración

### Primer usuario admin

Si no existe ningún usuario, dwSongs redirige a:

```text
/setup
```

Desde ahí se crea el primer administrador.

### Panel de usuarios

Disponible para usuarios admin en:

```text
/admin/users
```

Permite:

- crear usuarios,
- activar o desactivar usuarios,
- conceder o quitar rol admin,
- resetear contraseñas,
- ver último login.

### Histórico admin

Disponible en:

```text
/admin/downloads
```

Permite ver:

- usuario propietario,
- URL original,
- nombre original,
- uploader,
- metadatos editados,
- estado,
- rutas `incoming` y final,
- tamaños,
- fechas de acciones,
- auditoría por descarga.

También permite mostrar/ocultar columnas y filtrar por campos.

---

## Comandos de consola

Listar usuarios:

```bash
docker compose exec dwsongs python -m app.manage list-users
```

Crear usuario normal:

```bash
docker compose exec dwsongs python -m app.manage create-user usuario1 Password123
```

Crear usuario admin:

```bash
docker compose exec dwsongs python -m app.manage create-user admin Password123 --admin
```

Crear usuario con contraseña temporal generada:

```bash
docker compose exec dwsongs python -m app.manage create-user usuario1 --generate
```

Resetear contraseña:

```bash
docker compose exec dwsongs python -m app.manage reset-password usuario1 NuevaPassword123
```

Resetear contraseña generando una temporal:

```bash
docker compose exec dwsongs python -m app.manage reset-password usuario1 --generate
```

Activar usuario:

```bash
docker compose exec dwsongs python -m app.manage set-active usuario1 --active
```

Desactivar usuario:

```bash
docker compose exec dwsongs python -m app.manage set-active usuario1 --inactive
```

Hacer admin:

```bash
docker compose exec dwsongs python -m app.manage set-admin usuario1 --admin
```

Quitar admin:

```bash
docker compose exec dwsongs python -m app.manage set-admin usuario1 --no-admin
```

---

## Idiomas

Los idiomas se cargan desde:

```text
app/i18n/
```

Ejemplo:

```text
app/i18n/es.json
app/i18n/en.json
```

Para añadir un nuevo idioma:

1. Copia `es.json` o `en.json`.
2. Crea un nuevo fichero, por ejemplo:

```text
app/i18n/fr.json
```

3. Cambia `language_name` y traduce las claves.
4. Reinicia la aplicación.

El idioma aparecerá automáticamente en Ajustes.

---

## Datos que no deben subirse a GitHub

No subas nunca:

```text
.env
config/
data/
downloads/
jellyfin_music/
*.db
*.sqlite
*.sqlite3
```

El fichero `.gitignore` ya excluye estos elementos.

---

## Desarrollo local

Arrancar:

```bash
docker compose up -d
```

Ver logs:

```bash
docker compose logs -f
```

Reiniciar:

```bash
docker compose restart
```

Parar:

```bash
docker compose down
```

Recrear base de datos desde cero, solo si no necesitas conservar histórico:

```bash
docker compose down
rm -f data/dwsongs.db
docker compose up -d
```

En Windows PowerShell:

```powershell
docker compose down
Remove-Item data\dwsongs.db
docker compose up -d
```

---

## Estado del proyecto

Funcionalidades implementadas:

- Cola de URLs.
- Descarga de audio.
- Edición de metadatos.
- Envío a Jellyfin.
- Limpieza de incoming.
- Usuarios y admin.
- Histórico global admin.
- Auditoría básica.
- Idiomas externos.
- Filtros y columnas en histórico.

Pendientes posibles:

- Selector manual de release MusicBrainz.
- Mejoras visuales en filtros.
- Edición de idiomas desde panel admin.
- Migraciones de base de datos en lugar de recreación manual.

---

## Licencia

Este proyecto se distribuye bajo licencia **MIT**.

Consulta el fichero [`LICENSE`](LICENSE) para ver el texto completo de la licencia.

---

## Aviso

dwSongs no incluye contenido multimedia. El usuario es responsable de cumplir las condiciones de uso de las plataformas de origen y la legislación aplicable.
