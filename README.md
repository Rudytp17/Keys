# UPC Campus Quest 2026 - Analisis de Cadena de Ataque

> Proyecto academico de ciberseguridad - Analisis de un escenario controlado de attack chain que combina una aplicacion Electron aparentemente legitima con un modulo externo que actua como keylogger, incluyendo persistencia en Windows y exfiltracion a un servidor externo.

---

## Aviso legal y etico

Este repositorio tiene fines exclusivamente educativos y de investigacion en ciberseguridad defensiva. El codigo aqui presentado:

- Fue desarrollado en un laboratorio controlado y con fines de analisis.
- No debe usarse en sistemas de terceros sin autorizacion explicita.
- Su uso indebido puede constituir delito bajo la Ley N. 30096 (Ley de Delitos Informaticos, Peru) y la Ley N. 29733 (Proteccion de Datos Personales).
- El autor no se responsabiliza por el uso malintencionado del material.

---

## Descripcion general

El proyecto simula una cadena de ataque completa usando un juego Electron como vector de entrega:

```
Juego Electron (UPC.html)
        |
        v
main.js detecta Nivel 2
        |
        v
spawn wscript.exe -> Lanzar_Cody.vbs (oculto)
        |
        v
Cody.exe (keylogger empaquetado con PyInstaller)
        |
        v
install_persistence() -> HKCU\...\Run\UPCQuestService
        |
        v
Captura de teclado + ventana activa + info del equipo
        |
        v
Exfiltracion a Telegram cada 5 min o al cambiar de ventana
```
---

## Analisis por componente

| Archivo | Rol | Tecnica principal | Riesgo |
|---|---|---|---|
| package.json | Configuracion Electron | Empaqueta Cody.exe y Lanzar_Cody.vbs como extraResources | Medio |
| main.js | Proceso principal | spawn de wscript.exe con detached + windowsHide | Alto |
| preload.js | Puente seguro | contextBridge expone launchExternal | Bajo |
| UPC.html | Juego (fachada) | Dispara launchExternal al llegar al Nivel 2 | Medio |
| Lanzar_Cody.vbs | Lanzador oculto | sh.Run ..., 0, False (ventana oculta, sin espera) | Alto |
| Cody.py | Keylogger (carga util) | pynput + ctypes + persistencia + Telegram | Critico |

---

## Persistencia

El keylogger instala su propia persistencia en la clave Run de HKCU:

```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
    └── UPCQuestService = "C:\ruta\a\Cody.exe"
```

Caracteristicas:
- No requiere privilegios de administrador.
- Universal en todas las versiones de Windows.
- No depende de rutas fijas (sys.executable).
- Idempotente: se reejecuta en cada arranque.

---

## Exfiltracion

- Canal: Telegram Bot API (api.telegram.org).
- Frecuencia: cada 5 minutos o al cambiar de ventana activa.
- Contenido: teclas capturadas + ventana activa + info del equipo.
- Archivo local: %LOCALAPPDATA%\Recopilado.txt.
- Failover: 4 servicios para obtener IP publica.

---

## Indicadores de Compromiso (IOCs)

| Tipo | Valor |
|---|---|
| Clave de registro | HKCU\...\Run\UPCQuestService |
| Archivo local | %LOCALAPPDATA%\Recopilado.txt |
| Dominio de exfiltracion | api.telegram.org |
| Proceso padre | wscript.exe lanzando .exe |
| Proceso hijo | Cody.exe sin ventana visible |
| Firma digital | Ausente |

---

Proyecto desarrollado como parte del curso de Ciberseguridad - Analisis de cadena de ataque en entorno controlado.

---

## Licencia

Este proyecto se distribuye bajo la licencia MIT unicamente con fines educativos. El uso malintencionado queda estrictamente prohibido.
