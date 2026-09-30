# Deploy en Cloud Run

Guía paso a paso para publicar **Alabanza IDR** en Cloud Run desde tu
proyecto personal de GCP. Un solo servicio sirve la API y el frontend.

---

## 0. Estado actual (ya desplegado)

La app **ya está corriendo**. Los pasos 1 a 5 de esta guía ya se ejecutaron en
el proyecto `asistente-personal-unico`; quedan documentados para poder
reconstruir todo desde cero o replicarlo en otro proyecto.

| | |
|---|---|
| **URL** | <https://idra-alabanza-676487620897.southamerica-east1.run.app> |
| Proyecto | `asistente-personal-unico` |
| Región | `southamerica-east1` (São Paulo) |
| Servicio | `idra-alabanza` |
| Service account | `idra-alabanza-sa@asistente-personal-unico.iam.gserviceaccount.com` |
| API key | Secret Manager, secreto `idra-api-keys` |
| Escalado | 0 a 3 instancias (escala a cero: no se paga si nadie lo usa) |

Para ver la API key (es la que se pega en el panel de Administrador):

```bash
gcloud secrets versions access latest \
    --secret=idra-api-keys \
    --project=asistente-personal-unico
```

Recursos creados durante el deploy, por si alguna vez hay que limpiarlos: la
service account, el secreto `idra-api-keys`, el repositorio de Artifact
Registry `cloud-run-source-deploy` (imágenes construidas por Cloud Build) y
una entrada `WRITER` para la service account en el ACL del dataset `alabanza`.

---

## 1. Prerrequisitos

- Tener instalado el [SDK de gcloud](https://cloud.google.com/sdk/docs/install).
- Un proyecto de GCP con facturación habilitada.
- Las tablas de BigQuery ya creadas (son las mismas que usa la app Streamlit):
  - `<proyecto>.alabanza.canciones`
  - `<proyecto>.alabanza.set_lista`

Autenticarse y elegir el proyecto:

```bash
gcloud auth login
gcloud config set project TU_PROJECT_ID
```

Habilitar las APIs necesarias (una sola vez por proyecto):

```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    bigquery.googleapis.com \
    secretmanager.googleapis.com
```

---

## 2. Variables de trabajo

Definilas en la terminal desde la que vas a deployar (se usan en todos los
comandos que siguen):

```bash
export PROJECT_ID="asistente-personal-unico"   # tu proyecto
export REGION="southamerica-east1"             # São Paulo; la más cercana a AR
export SERVICE="idra-alabanza"
export SA_NAME="idra-alabanza-sa"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export DATASET="alabanza"
```

> El dataset de BigQuery y la región de Cloud Run pueden estar en regiones
> distintas: no hay problema, solo suma latencia mínima.

---

## 3. Service account del servicio

Cloud Run no debe correr con la cuenta por defecto (tiene permisos de más).
Se crea una dedicada con acceso únicamente a BigQuery:

```bash
gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Alabanza IDR (Cloud Run)"

# Permiso para lanzar queries (a nivel proyecto: es el mínimo posible).
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.jobUser"

# Permiso de lectura/escritura solo sobre el dataset de la app.
# (`bq add-iam-policy-binding` sobre datasets pide allowlisting, así que se
#  agrega la entrada al ACL del dataset, que es equivalente y sí funciona.)
bq show --format=prettyjson "${PROJECT_ID}:${DATASET}" > /tmp/ds.json

python3 - <<EOF
import json

ds = json.load(open("/tmp/ds.json"))
sa = "${SA_EMAIL}"

if not any(a.get("userByEmail") == sa for a in ds.get("access", [])):
    ds.setdefault("access", []).append({"role": "WRITER", "userByEmail": sa})

json.dump(ds, open("/tmp/ds.json", "w"))
EOF

bq update --source /tmp/ds.json "${PROJECT_ID}:${DATASET}"
```

`WRITER` sobre el dataset equivale a `bigquery.dataEditor`: alcanza para leer,
insertar, actualizar y borrar filas de las dos tablas, y no da acceso a nada
más del proyecto.

---

## 4. API key en Secret Manager

La API key protege todas las escrituras (alta, edición, borrado y publicación
del listado). Generá una larga y guardala en Secret Manager, nunca en el
código ni en una variable de entorno en texto plano.

```bash
# Generar una key aleatoria y guardarla como secreto.
python3 -c "import secrets; print(secrets.token_urlsafe(32))" \
    | tr -d '\n' \
    | gcloud secrets create idra-api-keys --data-file=-

# Ver la key generada (guardala en tu gestor de contraseñas).
gcloud secrets versions access latest --secret=idra-api-keys; echo

# Dejar que el servicio la lea.
gcloud secrets add-iam-policy-binding idra-api-keys \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
```

Se pueden tener **varias keys separadas por coma** (por ejemplo, una para el
panel web y otra para un script que carga canciones). Para rotarlas:

```bash
printf 'key-nueva,key-vieja' \
    | gcloud secrets versions add idra-api-keys --data-file=-

gcloud run services update "$SERVICE" --region="$REGION"  # toma la nueva versión
```

Cuando todos migraron a la key nueva, agregás otra versión con solo esa.

---

## 5. Deploy

Desde la raíz del repo (Cloud Build construye el `Dockerfile`
y publica la imagen automáticamente):

```bash
cd ~/Proyectos/IDRAlabanza

gcloud run deploy "$SERVICE" \
    --source . \
    --region="$REGION" \
    --service-account="$SA_EMAIL" \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=3 \
    --memory=512Mi \
    --cpu=1 \
    --timeout=60 \
    --set-env-vars="PROJECT_ID=${PROJECT_ID},TABLE_ID=${PROJECT_ID}.${DATASET}.canciones,SETLIST_TABLE_ID=${PROJECT_ID}.${DATASET}.set_lista,SETLIST_TTL_DAYS=7" \
    --set-secrets="API_KEYS=idra-api-keys:latest"
```

`--allow-unauthenticated` es necesario porque el equipo entra desde el
navegador sin cuenta de Google: la lectura es pública (igual que la app
Streamlit) y la escritura queda protegida por la API key.

Al terminar, gcloud imprime la URL del servicio. Guardala:

```bash
export URL=$(gcloud run services describe "$SERVICE" \
    --region="$REGION" --format='value(status.url)')

echo "$URL"
```

---

## 6. Verificación

```bash
# Salud del servicio. Va bajo /api porque el frontend de Google intercepta
# /healthz en los dominios *.run.app y devuelve un 404 propio.
curl -s "$URL/api/healthz"
# -> {"status":"ok"}

# Lectura pública
curl -s "$URL/api/songs" | head -c 300

# Escritura sin key: debe rechazar
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$URL/api/songs" \
    -H 'Content-Type: application/json' \
    -d '{"Cancion":"Prueba"}'
# -> 401
```

Abrí `$URL` en el navegador: deberías ver la vista de Dirección, poder
cambiar a Equipo y, en Administrador, entrar pegando la API key.

### Cargar canciones por API

Este es el caso de uso nuevo de la v2. Una canción:

```bash
export API_KEY="la-key-del-paso-4"

curl -s -X POST "$URL/api/songs" \
    -H "X-API-Key: $API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
        "Cancion": "Nombre De La Canción",
        "Notas_Piano": "https://drive.google.com/file/d/xxx/view",
        "Notas_Guitarra": "https://drive.google.com/file/d/yyy/view",
        "Letra": "https://drive.google.com/file/d/zzz/view",
        "Video_Bateria": "https://www.youtube.com/watch?v=aaa",
        "Audio": "https://music.youtube.com/watch?v=bbb",
        "Tono": "G",
        "Estado": "APRENDIENDO",
        "Tipo": "Lenta"
    }'
```

Varias de una (mandando un array). El `Numero` lo asigna el backend:

```bash
curl -s -X POST "$URL/api/songs" \
    -H "X-API-Key: $API_KEY" \
    -H 'Content-Type: application/json' \
    -d '[{"Cancion":"Una","Tono":"C"},{"Cancion":"Otra","Tipo":"Movida"}]'
```

La documentación interactiva de todos los endpoints queda en `$URL/docs`.

---

## 7. Correr en local

```bash
cd ~/Proyectos/IDRAlabanza

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Credenciales para que BigQuery funcione desde tu máquina.
gcloud auth application-default login

cp .env.example .env
# Editá .env: al menos API_KEYS con cualquier valor para poder probar el admin.

uvicorn backend.main:app --reload --port 8080
```

Abrí <http://localhost:8080>. `--reload` recarga el backend al guardar; para
el frontend alcanza con refrescar el navegador (no hay build step).

Probar la imagen de Docker tal cual va a correr en Cloud Run:

```bash
docker build -t idra-alabanza .

docker run --rm -p 8080:8080 \
    -e API_KEYS=local-test \
    -e PROJECT_ID="$PROJECT_ID" \
    -e TABLE_ID="${PROJECT_ID}.alabanza.canciones" \
    -e SETLIST_TABLE_ID="${PROJECT_ID}.alabanza.set_lista" \
    -e GOOGLE_APPLICATION_CREDENTIALS=/gcp/adc.json \
    -v "$HOME/.config/gcloud/application_default_credentials.json:/gcp/adc.json:ro" \
    idra-alabanza
```

---

## 8. Operación

**Ver logs:**

```bash
gcloud run services logs tail "$SERVICE" --region="$REGION"
```

**Actualizar la app** (después de cambiar código): repetir el comando del
paso 5. Cloud Run crea una revisión nueva y migra el tráfico solo si arranca
bien.

**Volver atrás:**

```bash
gcloud run revisions list --service="$SERVICE" --region="$REGION"

gcloud run services update-traffic "$SERVICE" \
    --region="$REGION" \
    --to-revisions=NOMBRE_DE_LA_REVISION=100
```

**Cambiar una variable sin redeployar:**

```bash
gcloud run services update "$SERVICE" \
    --region="$REGION" \
    --update-env-vars=SETLIST_TTL_DAYS=14
```

**Dominio propio** (opcional):

```bash
gcloud beta run domain-mappings create \
    --service="$SERVICE" \
    --domain=alabanza.tudominio.com \
    --region="$REGION"
```

Después hay que cargar en tu DNS los registros que imprime el comando.

---

## 9. Costo

Con `--min-instances=0` el servicio escala a cero: no se paga nada mientras
nadie lo usa, a costa de un arranque en frío de ~2-4 segundos en la primera
visita. Para un equipo chico, el uso entra holgado en la capa gratuita de
Cloud Run; el gasto relevante son las queries de BigQuery, que también son
mínimas (tablas de pocos KB).

Si el arranque en frío molesta, `--min-instances=1` lo elimina pero pasa a
cobrarse la instancia siempre encendida.

---

## 10. Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `API_KEYS` | *(vacío)* | Keys separadas por coma. **Sin ninguna, las escrituras devuelven 503.** |
| `PROJECT_ID` | del ADC | Proyecto GCP para el cliente de BigQuery. |
| `TABLE_ID` | `asistente-personal-unico.alabanza.canciones` | Tabla de canciones. |
| `SETLIST_TABLE_ID` | `asistente-personal-unico.alabanza.set_lista` | Tabla del listado. |
| `SETLIST_TTL_DAYS` | `7` | Días que un listado sigue publicado. |
| `SONGS_CACHE_TTL` | `600` | Segundos de caché de canciones (por instancia). |
| `SETLIST_CACHE_TTL` | `60` | Segundos de caché del listado (corto a propósito: el equipo tiene que ver un listado recién publicado). |
| `PORT` | `8080` | Lo inyecta Cloud Run; no hace falta setearla. |
