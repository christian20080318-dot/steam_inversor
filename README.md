# 🤖 Steam Investor Bot (Cloud & Soles Peruanos PEN)

Bot inteligente y automatizado de inversión y arbitraje para el Mercado de la Comunidad de Steam, diseñado para operar en la nube, gestionar un presupuesto en **Soles Peruanos (S/)**, diferenciar entre compras **Reales** y **Simuladas** mediante confirmación interactiva (*SÍ / NO*), y generar gráficos estadísticos de rendimiento.

---

## 🌟 Características Principales

1. **Precios Nativos en Soles (`currency=27`):**
   * Consulta directa al Mercado de Steam en moneda local peruana (S/).
   * Descuenta exactamente el **15% de comisión de Valve/juego** para calcular ganancias netas reales.
2. **Modo Dual (Cartera Real vs. Simulada con Confirmación SÍ / NO):**
   * Cuando el bot detecta una oportunidad, te envía una alerta a Telegram con botones:
     * `[✅ SÍ, compré el producto]`: Registra la compra en tu **Cartera Real** y descuenta el saldo invertido.
     * `[❌ NO, no lo compré]`: No gasta dinero real y registra la oportunidad en el **Simulador** para medir qué habría ocurrido.
3. **Gestión de Riesgo Dinámico y Escalable:**
   * Presupuesto base inicial: **S/ 500 PEN** (escala automáticamente si tu capital crece).
   * **Nivel Moderado:** Asigna hasta el 25% de tu efectivo disponible por compra.
   * **Límite Agresivo:** Máximo **3 operaciones agresivas al día** (descuentos extremos o menor liquidez).
   * **Dimensionamiento por Liquidez:** Nunca recomienda comprar más del 5% del volumen de ventas de las últimas 24 horas para evitar atrapar tu capital.
4. **Horario Operativo (07:00 AM a 10:00 PM - Hora de Perú):**
   * El bot escanea activamente cada 30 minutos entre las 7:00 AM y las 10:00 PM.
   * A las 10:00 PM ejecuta el **Cierre de Jornada**, genera reportes y entra en reposo hasta las 7:00 AM.
5. **Generador de Gráficos PNG (Matplotlib):**
   * Genera gráficos a **3 días**, **7 días (1 semana)** y **30 días (1 mes)**.
   * Genera gráficos de tendencia de ítems con líneas de compra y venta (*Take Profit*).
   * Envía las imágenes directamente por **Telegram** y adjuntas por **Gmail**.
6. **Consola de Inyección Manual (`manual_injector.py`):**
   * Permite inyectar compras manuales, ajustar fondos o forzar el cierre del día con generación de gráficos en cualquier momento.

---

## 📂 Estructura del Proyecto

```text
steam_investor_bot/
├── config.py              # Variables de configuración y límites
├── database.py            # Base de datos SQLite (portfolio, ledger y contadores)
├── steam_client.py        # Conexión a la API de Steam (PEN), parsing y URLs
├── risk_engine.py         # Filtros matemáticos, ROI neto y dimensionamiento
├── chart_generator.py     # Generador de gráficos PNG con Matplotlib
├── notifier.py            # Envíos a Telegram y Gmail SMTP
├── telegram_handler.py    # Escuchador interactivo de clics [SÍ / NO] y comandos
├── manual_injector.py     # Consola interactiva para inyectar compras o ajustar saldo
├── main.py                # Bucle principal y control de horario (7 AM - 10 PM)
├── requirements.txt       # Librerías de Python
├── Dockerfile             # Contenedor para la nube
├── docker-compose.yml     # Orquestación lista para VPS
├── knowledge/             # Base de conocimiento (libros y principios de inversión)
│   └── principios_inversion.md
└── charts/                # Carpeta donde se guardan los gráficos generados
```

---

## 🚀 Puesta en Marcha Rápida (Local o VPS)

### 1. Configurar variables de entorno
Copia el archivo `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita `.env` con tus datos:
* `TELEGRAM_BOT_TOKEN`: Token obtenido de [@BotFather](https://t.me/botfather).
* `TELEGRAM_CHAT_ID`: Tu ID de Telegram (puedes obtenerlo con [@userinfobot](https://t.me/userinfobot)).
* `GMAIL_USER` y `GMAIL_APP_PASSWORD`: Tu correo de Gmail y una Contraseña de Aplicación de 16 caracteres (generada en `Seguridad de la cuenta de Google > Contraseñas de aplicaciones`).

### 2. Ejecutar con Python directamente
```bash
pip install -r requirements.txt
python main.py
```

### 3. O ejecutar con Docker en la Nube (Recomendado 24/7)
```bash
docker compose up -d --build
```

---

## 🎮 Comandos de Telegram Disponibles

* `/resumen` o `/balance`: Muestra el estado actual de tu Cartera Real y Cartera Simulada.
* `/grafico 3`: Genera y te envía el gráfico de rendimiento de los últimos 3 días.
* `/grafico 7`: Genera y te envía el gráfico de rendimiento de la última semana.
* `/grafico 30`: Genera y te envía el gráfico de rendimiento del último mes.
* Escribir `si` / `no`: Confirma o descarta la última oportunidad pendiente.

---

## 🛠️ Uso de la Consola Manual (`manual_injector.py`)

Si compraste un ítem directamente en Steam y deseas registrarlo en el sistema sin esperar a que el bot lo detecte, o deseas modificar tu saldo en Soles:
```bash
python manual_injector.py
```
Opciones disponibles en el menú interactivo:
1. Registrar compra manual en Cartera Real.
2. Modificar / Recargar saldo de efectivo en Soles.
3. Forzar Cierre de Día (10:00 PM) y generar gráficos inmediatamente.
4. Ver todas las posiciones activas.
