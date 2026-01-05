# Despliegue en Producción

## Opciones de Despliegue

| Opción                       | Pros                   | Contras                      | Costo      |
| ---------------------------- | ---------------------- | ---------------------------- | ---------- |
| **PC Local**                 | Sin costo, fácil debug | Depende de tu internet/PC    | €0         |
| **VPS Windows**              | 24/7, internet estable | Costo mensual, setup inicial | €8-50/mes  |
| **VPS + Dashboard separado** | Escalable, seguro      | Más complejo                 | €15-60/mes |

---

## Despliegue en VPS Windows (Recomendado)

### 1. Requisitos del VPS

| Componente | Mínimo              | Recomendado         |
| ---------- | ------------------- | ------------------- |
| **OS**     | Windows Server 2019 | Windows Server 2022 |
| **RAM**    | 2 GB                | 4 GB                |
| **CPU**    | 2 vCores            | 4 vCores            |
| **Disco**  | 40 GB SSD           | 80 GB SSD           |
| **Red**    | 100 Mbps            | 1 Gbps              |

### 2. Proveedores Recomendados

| Proveedor                        | Precio/mes | Latencia   | Ideal para         |
| -------------------------------- | ---------- | ---------- | ------------------ |
| [Contabo](https://contabo.com)   | €8-15      | Frankfurt  | Empezar, económico |
| [ForexVPS](https://forexvps.net) | $25-50     | NY4/LD4    | Brokers US/UK      |
| [BeeksFX](https://beeksfx.com)   | $30-60     | Ultra-baja | Trading HFT        |

### 3. Instalación en VPS

```powershell
# 1. Conectar por RDP al VPS

# 2. Instalar Python 3.11+
# Descargar de https://python.org

# 3. Instalar Git
# Descargar de https://git-scm.com

# 4. Clonar repositorio
cd C:\
git clone https://github.com/tu-usuario/wsplumber.git
cd wsplumber

# 5. Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate

# 6. Instalar dependencias
pip install -r requirements.txt

# 7. Configurar .env
copy .env.example .env
notepad .env  # Editar con tus credenciales

# 8. Instalar MetaTrader 5
# Descargar del sitio de tu broker
# Iniciar sesión y configurar EA (si aplica)

# 9. Probar ejecución
python -m wsplumber.main
```

### 4. Configurar como Servicio Windows

Usar [NSSM](https://nssm.cc/) para ejecutar WSPlumber como servicio:

```powershell
# Descargar NSSM
# https://nssm.cc/download

# Instalar servicio
nssm install WSPlumber C:\wsplumber\venv\Scripts\python.exe -m wsplumber.main
nssm set WSPlumber AppDirectory C:\wsplumber
nssm set WSPlumber AppStdout C:\wsplumber\logs\service.log
nssm set WSPlumber AppStderr C:\wsplumber\logs\service-error.log

# Iniciar servicio
nssm start WSPlumber

# Verificar estado
nssm status WSPlumber
```

### 5. Configurar Firewall

```powershell
# Abrir puerto para dashboard
New-NetFirewallRule -DisplayName "WSPlumber Dashboard" -Direction Inbound -Port 8000 -Protocol TCP -Action Allow

# Opcional: Solo permitir tu IP
New-NetFirewallRule -DisplayName "WSPlumber Dashboard" -Direction Inbound -Port 8000 -Protocol TCP -Action Allow -RemoteAddress "TU.IP.PUBLICA"
```

---

## Configurar HTTPS (Opcional)

### Con Caddy (Reverse Proxy)

```powershell
# 1. Instalar Caddy
choco install caddy

# 2. Crear Caddyfile
# C:\Caddy\Caddyfile
```

```
wsplumber.tudominio.com {
    reverse_proxy localhost:8000
}
```

```powershell
# 3. Ejecutar Caddy
caddy run --config C:\Caddy\Caddyfile
```

---

## Monitoreo y Alertas

### Uptime Monitoring

Servicios gratuitos para monitorear que el bot está activo:

- [UptimeRobot](https://uptimerobot.com) - Gratis, 5 min interval
- [Freshping](https://freshping.io) - Gratis
- [Better Uptime](https://betteruptime.com) - Gratis tier

Configura check HTTP a `http://tu-vps-ip:8000/health`

### Alertas Telegram

Puedes configurar notificaciones vía Telegram editando el archivo de configuración o usando un notifier externo.

---

## Backup y Recuperación

### Backup Automático

```powershell
# Script de backup (guardar como backup.ps1)
$date = Get-Date -Format "yyyy-MM-dd"
$backupDir = "C:\backups\wsplumber-$date"

# Copiar configuración
Copy-Item C:\wsplumber\.env $backupDir\
Copy-Item C:\wsplumber\logs\* $backupDir\logs\ -Recurse

# Exportar datos de Supabase si es necesario
# pg_dump o usar panel de Supabase
```

Programar con Task Scheduler para ejecutar diariamente.

---

## Checklist de Producción

- [ ] VPS configurado con Windows Server
- [ ] Python 3.11+ instalado
- [ ] MT5 instalado y logueado
- [ ] WSPlumber instalado y configurado
- [ ] Servicio Windows creado (NSSM)
- [ ] Firewall configurado
- [ ] HTTPS configurado (opcional)
- [ ] Monitoreo de uptime activado
- [ ] Backups automáticos configurados
- [ ] Acceso RDP documentado (IP, usuario)
