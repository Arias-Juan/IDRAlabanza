# Alabanza IDR

Migración de la app Streamlit (v1, guardada en la tag `v1-streamlit`) a un servicio web pensado para
Cloud Run: **FastAPI** en el backend y HTML/CSS/JS vanilla en el frontend, con
el mismo aspecto y las mismas funcionalidades, más una API para cargar
canciones desde afuera.

Para publicarla, ver **[deploy.md](deploy.md)**.

## Estructura

```
backend/
  main.py            App FastAPI: routers + estáticos del frontend
  config.py          Configuración por variables de entorno
  models.py          Modelos Pydantic (validación de entrada y salida)
  security.py        Validación del header X-API-Key
  bigquery_repo.py   Toda la I/O contra BigQuery (SQL parametrizado)
  services.py        Lógica de negocio (armado del listado, texto a compartir)
  routers/
    songs.py         /api/songs
    setlist.py       /api/setlist
frontend/
  index.html         Las tres vistas: Dirección, Equipo, Administrador
  styles.css         Estilo heredado de la app Streamlit
  app.js             Render de tablas y llamadas a la API
```

El frontend no tiene build step: se edita y se refresca el navegador.

## Roles

Iguales a la app original, con el selector en el panel lateral:

- **Dirección** — canciones con estado `OK` (N°, canción, letra, audio, tipo).
- **Equipo** — listado publicado (con aviso de canciones borradas de la base),
  buscador por nombre o número y tabla completa del repertorio.
- **Compartir** — dos bloques de texto listos para copiar y pegar en el chat:
  el listado publicado y el repertorio completo (número y nombre, solo `OK`).
- **Administrador** — pide la API key; permite agregar canciones, eliminar,
  cambiar estado y armar/publicar el listado con reordenamiento.

## API

Las lecturas son públicas; las escrituras piden el header `X-API-Key`.
Documentación interactiva en `/docs`.

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/songs` | — | Todas las canciones. Params: `search`, `estado`. |
| `GET` | `/api/songs/{numero}` | — | Una canción. |
| `GET` | `/api/songs/texto-compartir` | — | Repertorio (solo estado `OK`) como texto para pegar en el chat. |
| `POST` | `/api/songs` | key | Alta. Acepta un objeto o una lista. |
| `PATCH` | `/api/songs/{numero}` | key | Actualización parcial. |
| `DELETE` | `/api/songs/{numero}` | key | Borrado. |
| `GET` | `/api/setlist` | — | Listado vigente + faltantes + texto a compartir. |
| `PUT` | `/api/setlist` | key | Publica un listado (`{"numeros": [3, 1, 3]}`). |
| `DELETE` | `/api/setlist` | key | Limpia el listado. |
| `POST` | `/api/auth/check` | key | Valida una API key. |
| `GET` | `/api/config` | — | Config pública del frontend. |
| `GET` | `/api/healthz` | — | Health check. |

## Diferencias con la v1

- El `Numero` de una canción nueva se calcula y se inserta en una sola
  sentencia de BigQuery, así dos altas simultáneas no se pisan.
- Todo el SQL de escritura es parametrizado (la v1 interpolaba el N° y el
  estado directamente en el string de la query).
- El acceso de administrador dejó de ser una contraseña en el código: ahora es
  una API key que vive en Secret Manager.
- Sin `API_KEYS` configurada, la escritura queda deshabilitada (503) en lugar
  de quedar abierta.

## Desarrollo local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
gcloud auth application-default login
cp .env.example .env      # completar API_KEYS
uvicorn backend.main:app --reload --port 8080
```
