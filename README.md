# dwSongs

Self-hosted web app for downloading audio from YouTube links, editing music metadata, and organizing the resulting files for Jellyfin.

The project is designed to run with Docker and to write music into a library folder that Jellyfin can scan.

---

## Contents

- [English](#english)
  - [Features](#features)
  - [Project structure](#project-structure)
  - [Requirements](#requirements)
  - [Quick start](#quick-start)
  - [Jellyfin configuration](#jellyfin-configuration)
  - [Music library layout](#music-library-layout)
  - [Users and administration](#users-and-administration)
  - [Language editor](#language-editor)
  - [Creating a new language](#creating-a-new-language)
  - [Console commands](#console-commands)
  - [Local development](#local-development)
  - [Publishing to GitHub](#publishing-to-github)
  - [Files that must not be committed](#files-that-must-not-be-committed)
  - [Roadmap](#roadmap)
  - [License](#license)
  - [Disclaimer](#disclaimer)
- [Español](#español)
  - [Características](#características)
  - [Estructura del proyecto](#estructura-del-proyecto)
  - [Requisitos](#requisitos)
  - [Puesta en marcha rápida](#puesta-en-marcha-rápida)
  - [Configuración de Jellyfin](#configuración-de-jellyfin)
  - [Estructura de la biblioteca musical](#estructura-de-la-biblioteca-musical)
  - [Usuarios y administración](#usuarios-y-administración)
  - [Editor de idiomas](#editor-de-idiomas)
  - [Crear un nuevo idioma](#crear-un-nuevo-idioma)
  - [Comandos de consola](#comandos-de-consola)
  - [Desarrollo local](#desarrollo-local)
  - [Subir el proyecto a GitHub](#subir-el-proyecto-a-github)
  - [Archivos que no deben subirse](#archivos-que-no-deben-subirse)
  - [Roadmap](#roadmap-1)
  - [Licencia](#licencia)
  - [Aviso](#aviso)

---

# English

## Features

- Download audio from YouTube URLs.
- Queue multiple URLs at once.
- Automatically fetch original video title and uploader.
- Stop metadata lookup after 5 seconds and allow manual editing.
- Edit title, artist, album, year, track number, disc number and genre.
- Fetch music metadata from MusicBrainz.
- Organize downloaded music into a Jellyfin-friendly folder structure.
- Send downloaded files to the Jellyfin music library.
- Refresh Jellyfin after moving music to the library.
- Clean temporary `incoming` files without deleting the final library file.
- User login and sessions.
- First admin setup from `/setup`.
- User administration panel.
- Password reset from the admin UI and from the console.
- Global admin history with users, metadata, paths, dates and audited actions.
- Column selector and filters in the admin history.
- Externalized interface languages using JSON files in [`app/i18n`](app/i18n).
- Web-based language editor in Settings.

---

## Project structure

```text
app/
  auth.py
  config.py
  coverart.py
  database.py
  downloader.py
  i18n_loader.py
  jellyfin.py
  language_admin.py
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
    language_editor.html
    login.html
    settings.html
    setup_admin.html
```

Useful root files:

- [`README.md`](README.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`LICENSE`](LICENSE)
- [`.env.example`](.env.example)
- [`.gitignore`](.gitignore)
- [`docker-compose.yml`](docker-compose.yml)
- [`docker-compose.prod.yml`](docker-compose.prod.yml)

---

## Requirements

- Docker
- Docker Compose
- Jellyfin, optional but recommended
- A shared music folder mounted both in dwSongs and Jellyfin

---

## Quick start

Clone the repository:

```bash
git clone https://github.com/YOUR_USER/dwsongs.git
cd dwsongs
```

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` if Jellyfin should be configured from the start:

```env
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=your_api_key
LIBRARY_MUSIC_PATH=/library/music
```

Start the app:

```bash
docker compose up -d
```

Open:

```text
http://localhost:8080
```

On the first run, create the initial admin user at:

```text
/setup
```

---

## Jellyfin configuration

Jellyfin can be configured from **Settings**.

You can set:

- Jellyfin URL.
- Jellyfin API key.
- Internal music library path.
- Automatic Jellyfin refresh.
- Interface language.

Common Jellyfin URL examples:

```text
http://jellyfin:8096
http://host.docker.internal:8096
http://192.168.1.50:8096
```

Recommended internal library path:

```text
/library/music
```

That path should point to the same physical folder Jellyfin uses for its music library.

---

## Music library layout

When a track is sent to Jellyfin, dwSongs writes the file using this structure:

```text
/library/music/Music/Artist/Album/01 - Title.mp3
```

After a successful copy:

- the temporary `incoming` file is removed;
- the final Jellyfin library file is kept;
- the action is recorded in the admin history.

---

## Users and administration

### Initial admin user

If no users exist, dwSongs redirects to:

```text
/setup
```

Use that page to create the first administrator.

### User administration

Available for admin users at:

```text
/admin/users
```

The admin panel allows you to:

- create users;
- activate or deactivate users;
- grant or remove admin permissions;
- reset passwords;
- see the last login time.

### Admin history

Available at:

```text
/admin/downloads
```

The admin history includes:

- owner user;
- original URL;
- original video title;
- uploader;
- edited metadata;
- status;
- `incoming` path;
- final library path;
- file sizes;
- action dates;
- per-download audit log.

It also includes column visibility controls and filters.

---

## Language editor

The language editor is available for admin users from:

```text
/settings/languages
```

You can also open it from **Settings** using the **Open language editor** button.

The editor allows you to:

- select an existing language;
- edit all text keys;
- compare the selected language with the Spanish base text;
- see missing keys;
- filter by key or text;
- add new translation keys;
- create a new language file by copying an existing one.

Language files are stored in:

```text
app/i18n/
```

Example files:

```text
app/i18n/es.json
app/i18n/en.json
```

---

## Creating a new language

There are two supported ways to add a language.

### Option 1: Use the web editor

1. Log in with an admin user.
2. Go to:

```text
/settings/languages
```

3. In **Create new language**, enter a language code.

Examples:

```text
fr
de
it
pt
ca
```

4. Choose the language to copy from, usually `es` or `en`.
5. Click **Create language**.
6. Edit the generated values.
7. Click **Save language**.
8. Restart the app if the new language does not appear immediately in Settings.

### Option 2: Add the JSON file manually

Copy an existing language file:

```bash
cp app/i18n/es.json app/i18n/fr.json
```

Edit the new file:

```bash
nano app/i18n/fr.json
```

Make sure the file contains a readable language name:

```json
{
    "language_name": "Français"
}
```

Then restart the app:

```bash
docker compose restart
```

The new language should appear in Settings.

---

## Console commands

List users:

```bash
docker compose exec dwsongs python -m app.manage list-users
```

Create a normal user:

```bash
docker compose exec dwsongs python -m app.manage create-user user1 Password123
```

Create an admin user:

```bash
docker compose exec dwsongs python -m app.manage create-user admin Password123 --admin
```

Create a user with a generated temporary password:

```bash
docker compose exec dwsongs python -m app.manage create-user user1 --generate
```

Reset a password:

```bash
docker compose exec dwsongs python -m app.manage reset-password user1 NewPassword123
```

Reset a password with a generated temporary password:

```bash
docker compose exec dwsongs python -m app.manage reset-password user1 --generate
```

Activate a user:

```bash
docker compose exec dwsongs python -m app.manage set-active user1 --active
```

Deactivate a user:

```bash
docker compose exec dwsongs python -m app.manage set-active user1 --inactive
```

Grant admin permissions:

```bash
docker compose exec dwsongs python -m app.manage set-admin user1 --admin
```

Remove admin permissions:

```bash
docker compose exec dwsongs python -m app.manage set-admin user1 --no-admin
```

---

## Local development

Start:

```bash
docker compose up -d
```

View logs:

```bash
docker compose logs -f
```

Restart:

```bash
docker compose restart
```

Stop:

```bash
docker compose down
```

Recreate the database from scratch, only if the existing history is not needed:

```bash
docker compose down
rm -f data/dwsongs.db
docker compose up -d
```

On Windows PowerShell:

```powershell
docker compose down
Remove-Item data\dwsongs.db
docker compose up -d
```

---

## Publishing to GitHub

Before publishing, make sure private data is not going to be committed.

Check the repository status:

```bash
git status
```

Check ignored files if needed:

```bash
git status --ignored
```

Initialize Git if the project is not already a repository:

```bash
git init
```

Add files:

```bash
git add .
```

Review what will be committed:

```bash
git status
```

Create the first commit:

```bash
git commit -m "Initial dwSongs release"
```

Set the main branch:

```bash
git branch -M main
```

Create an empty repository on GitHub.

Do not initialize the GitHub repository with README, `.gitignore` or license if those files already exist locally.

Add the remote repository:

```bash
git remote add origin https://github.com/YOUR_USER/dwsongs.git
```

Push the project:

```bash
git push -u origin main
```

For later updates:

```bash
git add .
git commit -m "Describe the change"
git push
```

---

## Files that must not be committed

Do not commit runtime data, secrets, downloaded media or local databases.

The following paths are ignored by [`.gitignore`](.gitignore):

```text
.env
config/
data/
downloads/
jellyfin_music/
*.db
*.sqlite
*.sqlite3
*.mp3
*.flac
*.m4a
*.zip
```

---

## Roadmap

Possible future improvements:

- Manual MusicBrainz release selector.
- Better batch error reporting.
- Export admin history to CSV or XLSX.
- Database migrations instead of manual database recreation.
- More language editor tools.

---

## License

This project is distributed under the **MIT License**.

See [`LICENSE`](LICENSE) for the full license text.

---

## Disclaimer

dwSongs does not include any media content. Users are responsible for complying with the terms of service of source platforms and all applicable laws.

---

# Español

## Características

- Descarga de audio desde URLs de YouTube.
- Cola de varias URLs de una sola vez.
- Obtención automática del nombre original del vídeo y del uploader.
- Corte de la búsqueda de información a los 5 segundos y edición manual si no se encuentra nada.
- Edición de título, artista, álbum, año, número de pista, número de disco y género.
- Búsqueda de metadatos con MusicBrainz.
- Organización automática de música en una estructura compatible con Jellyfin.
- Envío de ficheros descargados a la biblioteca musical de Jellyfin.
- Refresco de Jellyfin tras mover música a la biblioteca.
- Limpieza de ficheros temporales de `incoming` sin borrar el fichero final de la biblioteca.
- Login de usuarios y sesiones.
- Creación del primer administrador desde `/setup`.
- Panel de administración de usuarios.
- Reset de contraseñas desde la interfaz admin y desde consola.
- Histórico admin global con usuarios, metadatos, rutas, fechas y acciones auditadas.
- Selector de columnas y filtros en el histórico admin.
- Idiomas externos mediante ficheros JSON en [`app/i18n`](app/i18n).
- Editor web de idiomas dentro de Configuración.

---

## Estructura del proyecto

```text
app/
  auth.py
  config.py
  coverart.py
  database.py
  downloader.py
  i18n_loader.py
  jellyfin.py
  language_admin.py
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
    language_editor.html
    login.html
    settings.html
    setup_admin.html
```

Archivos útiles en la raíz:

- [`README.md`](README.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`LICENSE`](LICENSE)
- [`.env.example`](.env.example)
- [`.gitignore`](.gitignore)
- [`docker-compose.yml`](docker-compose.yml)
- [`docker-compose.prod.yml`](docker-compose.prod.yml)

---

## Requisitos

- Docker
- Docker Compose
- Jellyfin, opcional pero recomendado
- Una carpeta musical compartida entre dwSongs y Jellyfin

---

## Puesta en marcha rápida

Clona el repositorio:

```bash
git clone https://github.com/TU_USUARIO/dwsongs.git
cd dwsongs
```

Copia el fichero de entorno de ejemplo:

```bash
cp .env.example .env
```

Edita `.env` si quieres dejar Jellyfin preconfigurado:

```env
JELLYFIN_URL=http://jellyfin:8096
JELLYFIN_API_KEY=tu_api_key
LIBRARY_MUSIC_PATH=/library/music
```

Levanta la aplicación:

```bash
docker compose up -d
```

Abre:

```text
http://localhost:8080
```

En el primer arranque, crea el usuario administrador inicial en:

```text
/setup
```

---

## Configuración de Jellyfin

Jellyfin se puede configurar desde **Ajustes**.

Puedes definir:

- URL de Jellyfin.
- API Key de Jellyfin.
- Ruta interna de la biblioteca musical.
- Refresco automático de Jellyfin.
- Idioma de la interfaz.

Ejemplos habituales de URL:

```text
http://jellyfin:8096
http://host.docker.internal:8096
http://192.168.1.50:8096
```

Ruta interna recomendada:

```text
/library/music
```

Esa ruta debe apuntar a la misma carpeta física que Jellyfin usa como biblioteca musical.

---

## Estructura de la biblioteca musical

Cuando una canción se envía a Jellyfin, dwSongs escribe el fichero usando esta estructura:

```text
/library/music/Music/Artista/Álbum/01 - Título.mp3
```

Después de una copia correcta:

- se elimina el fichero temporal de `incoming`;
- se conserva el fichero final de la biblioteca Jellyfin;
- se registra la acción en el histórico admin.

---

## Usuarios y administración

### Usuario admin inicial

Si no existe ningún usuario, dwSongs redirige a:

```text
/setup
```

Desde esa pantalla se crea el primer administrador.

### Administración de usuarios

Disponible para usuarios admin en:

```text
/admin/users
```

El panel permite:

- crear usuarios;
- activar o desactivar usuarios;
- conceder o quitar permisos admin;
- resetear contraseñas;
- ver la fecha del último login.

### Histórico admin

Disponible en:

```text
/admin/downloads
```

El histórico admin incluye:

- usuario propietario;
- URL original;
- nombre original del vídeo;
- uploader;
- metadatos editados;
- estado;
- ruta `incoming`;
- ruta final de biblioteca;
- tamaños;
- fechas de acciones;
- auditoría por descarga.

También incluye controles para mostrar u ocultar columnas y filtros por campos.

---

## Editor de idiomas

El editor de idiomas está disponible para usuarios admin en:

```text
/settings/languages
```

También se puede abrir desde **Ajustes** con el botón **Abrir editor de idiomas**.

El editor permite:

- seleccionar un idioma existente;
- editar todas las claves de texto;
- comparar el idioma seleccionado con el texto base en español;
- ver claves pendientes;
- filtrar por clave o texto;
- añadir nuevas claves de traducción;
- crear un nuevo idioma copiando desde uno existente.

Los idiomas se guardan en:

```text
app/i18n/
```

Ejemplos:

```text
app/i18n/es.json
app/i18n/en.json
```

---

## Crear un nuevo idioma

Hay dos formas de añadir un idioma.

### Opción 1: usar el editor web

1. Inicia sesión con un usuario administrador.
2. Entra en:

```text
/settings/languages
```

3. En **Crear nuevo idioma**, escribe el código del idioma.

Ejemplos:

```text
fr
de
it
pt
ca
```

4. Elige el idioma desde el que quieres copiar, normalmente `es` o `en`.
5. Pulsa **Crear idioma**.
6. Edita los valores generados.
7. Pulsa **Guardar idioma**.
8. Reinicia la aplicación si el nuevo idioma no aparece inmediatamente en Ajustes.

### Opción 2: añadir el JSON manualmente

Copia un idioma existente:

```bash
cp app/i18n/es.json app/i18n/fr.json
```

Edita el nuevo fichero:

```bash
nano app/i18n/fr.json
```

Asegúrate de que contiene un nombre legible para el idioma:

```json
{
    "language_name": "Français"
}
```

Reinicia la aplicación:

```bash
docker compose restart
```

El nuevo idioma debería aparecer en Ajustes.

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

Recrear la base de datos desde cero, solo si no necesitas conservar el histórico:

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

## Subir el proyecto a GitHub

Antes de publicar el proyecto, comprueba que no vas a subir datos privados.

Revisa el estado del repositorio:

```bash
git status
```

Si quieres ver también los archivos ignorados:

```bash
git status --ignored
```

Inicializa Git si todavía no es un repositorio:

```bash
git init
```

Añade los archivos:

```bash
git add .
```

Revisa lo que se va a subir:

```bash
git status
```

Crea el primer commit:

```bash
git commit -m "Initial dwSongs release"
```

Define la rama principal:

```bash
git branch -M main
```

Crea un repositorio vacío en GitHub.

No inicialices el repositorio de GitHub con README, `.gitignore` ni licencia si esos archivos ya existen localmente.

Añade el remoto:

```bash
git remote add origin https://github.com/TU_USUARIO/dwsongs.git
```

Sube el proyecto:

```bash
git push -u origin main
```

Para futuras actualizaciones:

```bash
git add .
git commit -m "Describe the change"
git push
```

---

## Archivos que no deben subirse

No subas datos runtime, secretos, descargas ni bases de datos locales.

Estos elementos están ignorados en [`.gitignore`](.gitignore):

```text
.env
config/
data/
downloads/
jellyfin_music/
*.db
*.sqlite
*.sqlite3
*.mp3
*.flac
*.m4a
*.zip
```

---

## Roadmap

Posibles mejoras futuras:

- Selector manual de release de MusicBrainz.
- Mejor reporte de errores en acciones masivas.
- Exportar histórico admin a CSV o XLSX.
- Migraciones de base de datos en lugar de recreación manual.
- Más herramientas para el editor de idiomas.

---

## Licencia

Este proyecto se distribuye bajo licencia **MIT**.

Consulta [`LICENSE`](LICENSE) para ver el texto completo de la licencia.

---

## Aviso

dwSongs no incluye contenido multimedia. El usuario es responsable de cumplir las condiciones de uso de las plataformas de origen y la legislación aplicable.
