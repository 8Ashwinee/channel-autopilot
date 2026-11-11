
# channel-autopilot

Ejecuta tus canales de YouTube automáticamente utilizando tus propias claves: descubre qué busca la gente, crea guiones y vídeos narrados, publica contenido de forma programada en YouTube, Instagram y Facebook, gestiona varios canales y supervisa todo desde un panel privado.

## Descripción general

channel-autopilot automatiza el flujo de trabajo de creación y publicación de contenido:

```text
autopilot research → tu herramienta de IA → autopilot make → queue/ → autopilot run → YouTube · Instagram · Facebook
```

- **Investigación:** descubre palabras clave y búsquedas relacionadas mediante Google Ads Keyword Planner.
- **Creación de contenido:** prepara un archivo `video.yml` para cada tema con títulos, datos y guiones.
- **Generación de vídeos:** convierte los guiones en vídeos narrados con voz, subtítulos y miniaturas.
- **Publicación:** programa y publica contenido respetando los límites diarios de cada plataforma.
- **Rotación de canales:** automatiza la publicación entre varios canales, uno por día.
- **Panel de control:** consulta estadísticas, investigaciones y actividad desde un panel privado alojado en tu propia cuenta de AWS.

**Importante:** el proyecto no incluye claves ni credenciales. Cada usuario debe proporcionar su propio proyecto de Google Cloud (YouTube API, Keyword Planner y Search Console), su propia aplicación de Meta para publicar en Instagram/Facebook y su propia cuenta de AWS para el panel de control.

Consulta [docs/GOOGLE-SETUP.md](GOOGLE-SETUP.md) para comenzar con la configuración de Google.

## Componentes principales

| Componente | Descripción | Requisitos |
|---|---|---|
| Publisher | Publica vídeos, imágenes y enlaces en YouTube, Instagram y Facebook. Gestiona límites diarios, reintentos y registros de publicación. | Python 3.10+ y credenciales de las plataformas |
| Maker | Convierte archivos `video.yml` en vídeos MP4 narrados con subtítulos y miniaturas. | Python 3.10–3.12, ffmpeg, espeak-ng y Chromium |
| Research | Investiga palabras clave mediante Google Ads Keyword Planner y proporciona volumen de búsquedas, competencia y ofertas publicitarias. | Cuenta de Google Cloud, Google Ads y acceso básico a Google Ads API |
| Rotation | Automatiza la investigación, creación y publicación de contenido en varios canales. | Los componentes anteriores y una herramienta para generar guiones |
| Dashboard | Ofrece estadísticas por canal, términos de búsqueda, rotación de publicaciones e investigaciones desde un panel privado. | Una cuenta de AWS |

El proyecto no crea cuentas, obtiene aprobaciones de las plataformas ni garantiza visualizaciones. Debes proporcionar tus propias credenciales de YouTube, Instagram y Facebook. Consulta [docs/SETUP.md](SETUP.md) para obtener instrucciones adicionales.

## Inicio rápido

### 1. Clonar el repositorio

```bash
git clone https://github.com/<you>/channel-autopilot && cd channel-autopilot
```

### 2. Crear y activar un entorno virtual

```bash
python3.12 -m venv .venv && . .venv/bin/activate
```

### 3. Instalar el proyecto y sus dependencias

```bash
pip install -e '.[youtube,maker,research]'
```

### 4. Instalar Chromium para Playwright

```bash
playwright install chromium
```

### 5. Instalar las dependencias del sistema

En macOS:

```bash
brew install ffmpeg espeak-ng
```

En Ubuntu o Debian:

```bash
apt install ffmpeg espeak-ng
```

### 6. Inicializar el proyecto

```bash
autopilot init
```

Este comando crea `config.yml`, `queue/` y `secrets/`.

### 7. Preparar el generador de vídeos

```bash
autopilot make --setup
```

Descarga el modelo de voz necesario (aproximadamente 330 MB, solo una vez).

### 8. Crear tu primer vídeo

```bash
autopilot make examples/videos/three-habits-short.yml --queue
```

Genera la voz, el vídeo y la miniatura, y añade el resultado a la cola de publicaciones.

### 9. Revisar las publicaciones programadas

```bash
autopilot plan
```

### 10. Ejecutar una prueba sin publicar contenido

```bash
autopilot run --dry-run
```

Este comando simula la ejecución sin publicar nada.

## Después de configurar tus credenciales

Una vez que hayas añadido tus credenciales a `config.yml`, puedes utilizar los siguientes comandos:

```bash
autopilot doctor
autopilot youtube-auth
autopilot run --report
autopilot research
```

- `autopilot doctor`: comprueba qué credenciales faltan.
- `autopilot youtube-auth`: inicia sesión en YouTube mediante el navegador.
- `autopilot run --report`: publica el contenido pendiente del día y genera un informe.
- `autopilot research`: busca temas interesantes para nuevos vídeos.

Consulta [docs/SETUP.md](SETUP.md) para configurar las plataformas y [docs/RESEARCH.md](RESEARCH.md) para obtener más información sobre la investigación de palabras clave.

Para gestionar varios canales automáticamente, consulta [docs/ROTATION.md](ROTATION.md).

---

[English README](../README.md)
