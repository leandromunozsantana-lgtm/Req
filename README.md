# Load Test — Railway Deployment

## Archivos
- `main.py` — script principal
- `requirements.txt` — dependencias
- `Procfile` — comando de inicio para Railway

## Despliegue en Railway

1. Crea cuenta en https://railway.app
2. New Project → Deploy from GitHub repo
   (sube estos archivos a un repo de GitHub primero)
3. En Railway → tu proyecto → **Variables**:

   | Variable       | Valor                  |
   |----------------|------------------------|
   | `BEARER_TOKEN` | eyJhbGci...tu_token    |
   | `TOTAL_REQ`    | 50000  (opcional)      |
   | `CONCURRENCY`  | 100    (opcional)      |

4. Deploy → ve los logs en tiempo real

## Cambiar el token sin redesplegar

Railway → tu proyecto → Variables → edita `BEARER_TOKEN` → Save
El servicio se reinicia automáticamente con el nuevo token.

## Ver logs en vivo

Railway → tu proyecto → Deployments → Ver logs
Verás cada respuesta ✅/❌ en tiempo real.
