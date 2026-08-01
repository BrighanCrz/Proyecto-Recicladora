# Sistema Recicladora
from __future__ import annotations

# Librerias estandar:
# - json: guarda y lee los datos del sistema
# - os: rutas, archivos y variables de entorno
# - shutil: copia archivos, usado en respaldos
# - datetime/timedelta: fechas actuales y calculo de pagos
# - wraps: conserva metadatos en decoradores
# - uuid4: genera ids unicos cortos
import json
import os
import shutil
from datetime import datetime, timedelta
from functools import wraps
from uuid import uuid4

# Flask:
# - Flask: crea la aplicacion
# - flash: mensajes temporales en pantalla
# - redirect/url_for: redirecciones entre rutas
# - render_template_string: renderiza HTML escrito dentro del archivo
# - request: datos enviados por formularios
# - session: mantiene la sesion del usuario autenticado
from flask import (
    Flask,
    flash,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)

# Markup permite devolver fragmentos HTML ya listos para renderizar
from markupsafe import Markup


# -------------------------------------------------------------------
# CONFIGURACION GENERAL DEL PROYECTO
# -------------------------------------------------------------------
# Este proyecto esta hecho como una primera version funcional en un solo archivo.
# No esta pensado como producto final de produccion, sino como base academica o demo.
APP_NAME = "CycleOS"
COMPANY_NAME = "BCR Systems"
DATA_FILE = "cycleos_data.json"
BACKUP_DIR = "cycleos_backups"

# Credenciales del superadmin.
# Ojo: aqui estan en texto plano, lo cual no es seguro para produccion.
SUPERADMIN_USER = "superadmin"
SUPERADMIN_PASSWORD = "admin123"

# Codigo de acceso general. Puede venir desde variable de entorno.
ACCESS_CODE = os.getenv("CYCLEOS_ACCESS_CODE", "BCR2026")

# Alias permitidos para el superadmin.
SUPERADMIN_ALIASES = {
    ("superadmin", "admin123"),
    ("SpAdmin", "AdminBCR1718"),
}

# Conjunto de codigos de acceso validos.
ACCESS_CODES = {ACCESS_CODE, "BcrSystems2026"}

# Conversion de kilogramos a libras.
KG_TO_LB = 2.20462

# Precios sugeridos por material en kg.
# Luego se usan para autollenar formularios.
SUGGESTED_PRICES_KG = {
    "aluminio": 4.50,
    "cobre": 25.00,
    "lata": 0.36,
    "carton": 1.25,
    "hierro": 2.75,
    "hierro primera": 0.90,
    "hierro segunda": 0.50,
    "hierro colado": 0.72,
    "bronce": 14.50,
    "laton": 14.50,
    "antimonio": 3.00,
    "plomo": 3.50,
    "bateria": 2.75,
    "papel": 0.45,
    "vidrio": 0.18,
    "soplado": 1.80,
    "duro": 2.00,
    "pet": 1.72,
}

# Construye una tabla de precios sugeridos en kg y lb.
SUGGESTED_PRICES = {
    material: {"kg": price, "lb": round(price / KG_TO_LB, 2)}
    for material, price in SUGGESTED_PRICES_KG.items()
}


# -------------------------------------------------------------------
# INICIALIZACION DE FLASK
# -------------------------------------------------------------------
app = Flask(__name__)

# Clave secreta para sesiones.
# En produccion deberia venir de variable de entorno y ser robusta.
app.secret_key = os.getenv("CYCLEOS_SECRET_KEY", "cycleos-dev-secret-change-me")


# -------------------------------------------------------------------
# UTILIDADES GENERALES
# -------------------------------------------------------------------
def money(value: float) -> str:
    """Da formato monetario tipo quetzales."""
    return f"Q{float(value):,.2f}"


# Registra el filtro para usarlo en plantillas Jinja: {{ valor|money }}
app.jinja_env.filters["money"] = money


def now_text() -> str:
    """Fecha y hora actual en texto."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text() -> str:
    """Solo la fecha actual en texto."""
    return datetime.now().strftime("%Y-%m-%d")


def uid() -> str:
    """Genera un id corto unico para registros."""
    return uuid4().hex[:10]


# -------------------------------------------------------------------
# DATOS INICIALES DEL SISTEMA
# -------------------------------------------------------------------
def default_data() -> dict:
    """
    Crea la estructura base del sistema cuando aun no existe el archivo JSON.
    Incluye empresas de ejemplo, compras, ventas, inventario, clientes, rutas,
    notas, pagos y lista de respaldos.
    """
    next_payment = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "companies": [
            {
                "id": "eco-metal",
                "name": "Eco Metal Guatemala",
                "logo": "EM",
                "primary_color": "#0f766e",
                "background": "linear-gradient(135deg, #ecfeff, #f8fafc)",
                "user": "eco",
                "password": "1234",
                "payment_date": next_payment,
                "active": True,
                "created_at": today_text(),
            },
            {
                "id": "recicla-norte",
                "name": "Recicla Norte",
                "logo": "RN",
                "primary_color": "#2563eb",
                "background": "linear-gradient(135deg, #eff6ff, #f8fafc)",
                "user": "norte",
                "password": "1234",
                "payment_date": next_payment,
                "active": False,
                "created_at": today_text(),
            },
        ],
        "records": {
            "eco-metal": {
                "purchases": [
                    {
                        "id": uid(),
                        "date": today_text(),
                        "material": "cobre",
                        "weight": 18,
                        "price": 45,
                        "supplier": "Carlos Lopez",
                    },
                    {
                        "id": uid(),
                        "date": today_text(),
                        "material": "aluminio",
                        "weight": 32,
                        "price": 8,
                        "supplier": "Ruta Central",
                    },
                ],
                "sales": [
                    {
                        "id": uid(),
                        "date": today_text(),
                        "material": "cobre",
                        "weight": 15,
                        "price": 54,
                        "customer": "Fundidora Maya",
                    }
                ],
                "inventory": [
                    {"id": uid(), "material": "cobre", "weight": 3, "location": "Bodega A"},
                    {"id": uid(), "material": "aluminio", "weight": 32, "location": "Bodega B"},
                ],
                "customers": [
                    {
                        "id": uid(),
                        "name": "Fundidora Maya",
                        "phone": "5555-0101",
                        "address": "Zona 12, Guatemala",
                        "material": "cobre",
                        "notes": "Compra semanal.",
                    }
                ],
                "routes": [
                    {
                        "id": uid(),
                        "customer": "Fundidora Maya",
                        "address": "Zona 12, Guatemala",
                        "material": "cobre",
                        "weight": 15,
                        "driver": "Luis Perez",
                        "status": "en camino",
                    }
                ],
                "notes": [
                    {
                        "id": uid(),
                        "date": today_text(),
                        "title": "Revision de bascula",
                        "body": "Programar mantenimiento preventivo esta semana.",
                    }
                ],
            },
            "recicla-norte": {
                "purchases": [],
                "sales": [],
                "inventory": [],
                "customers": [],
                "routes": [],
                "notes": [],
            },
        },
        "payments": [
            {
                "id": uid(),
                "company_id": "eco-metal",
                "date": today_text(),
                "amount": 399,
                "status": "pagado",
                "notes": "Plan mensual inicial",
            }
        ],
        "backups": [],
    }


# -------------------------------------------------------------------
# PERSISTENCIA DE DATOS EN JSON
# -------------------------------------------------------------------
def load_data() -> dict:
    """
    Carga los datos desde el JSON.
    Si no existe el archivo, crea la estructura por defecto y la guarda.
    """
    if not os.path.exists(DATA_FILE):
        data = default_data()
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data: dict) -> None:
    """Guarda todo el estado del sistema en el archivo JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def company_records(data: dict, company_id: str) -> dict:
    """
    Garantiza que una empresa tenga sus modulos base.
    Si no existen, los crea.
    """
    data["records"].setdefault(
        company_id,
        {
            "purchases": [],
            "sales": [],
            "inventory": [],
            "customers": [],
            "routes": [],
            "notes": [],
        },
    )
    return data["records"][company_id]


def weight_to_kg(weight: float, unit: str = "kg") -> float:
    """Convierte a kilogramos si el peso viene en libras."""
    return float(weight) / KG_TO_LB if unit == "lb" else float(weight)


def find_company(data: dict, company_id: str) -> dict | None:
    """Busca una empresa por su id."""
    return next((item for item in data["companies"] if item["id"] == company_id), None)


def calculate_totals(records: dict) -> dict:
    """
    Calcula totales operativos de una empresa:
    - total en compras
    - total en ventas
    - ganancia
    - peso total en inventario
    - cantidad de clientes, rutas y notas
    """
    purchases = sum(float(i["weight"]) * float(i["price"]) for i in records["purchases"])
    sales = sum(float(i["weight"]) * float(i["price"]) for i in records["sales"])
    inventory_weight = sum(weight_to_kg(i["weight"], i.get("unit", "kg")) for i in records["inventory"])
    return {
        "purchases": purchases,
        "sales": sales,
        "profit": sales - purchases,
        "inventory_weight": inventory_weight,
        "customers": len(records["customers"]),
        "routes": len(records["routes"]),
        "notes": len(records["notes"]),
    }


def global_stats(data: dict) -> dict:
    """
    Calcula estadisticas globales del SaaS para el panel superadmin.
    Recorre todas las empresas y suma sus indicadores.
    """
    active = sum(1 for c in data["companies"] if c["active"])
    suspended = len(data["companies"]) - active
    revenue = sum(float(p["amount"]) for p in data["payments"] if p["status"] == "pagado")
    estimated = active * 399

    total_sales = 0
    total_purchases = 0
    for company in data["companies"]:
        totals = calculate_totals(company_records(data, company["id"]))
        total_sales += totals["sales"]
        total_purchases += totals["purchases"]

    return {
        "companies": len(data["companies"]),
        "active": active,
        "suspended": suspended,
        "revenue": revenue,
        "estimated": estimated,
        "sales": total_sales,
        "purchases": total_purchases,
        "profit": total_sales - total_purchases,
    }


def create_backup(data: dict, reason: str = "automatico") -> str:
    """
    Crea un respaldo del JSON actual.
    Ademas registra ese respaldo dentro del mismo sistema.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"cycleos_backup_{stamp}.json"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    save_data(data)
    shutil.copy(DATA_FILE, backup_path)

    data["backups"].append(
        {"id": uid(), "date": now_text(), "file": backup_path, "reason": reason}
    )
    save_data(data)
    return backup_path


# -------------------------------------------------------------------
# CONTROL DE ACCESO
# -------------------------------------------------------------------
def login_required(role: str | None = None):
    """
    Decorador para proteger rutas.
    - Si no hay sesion, manda al login
    - Si el rol no coincide, bloquea el acceso
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "role" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("No tienes permisos para acceder a esa seccion.", "warning")
                return redirect(url_for("login"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


# -------------------------------------------------------------------
# PLANTILLA BASE DE TODA LA APP
# -------------------------------------------------------------------
# Esta cadena contiene el HTML principal con Bootstrap, estilos,
# sidebar, mensajes flash y un pequeño script para sugerir precios.
# En el archivo original es bastante largo; aqui lo mantengo resumido
# para que el enfoque quede en la logica del proyecto.
BASE_TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} - CycleOS</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    /* Aqui van todos los estilos globales del login, sidebar, tarjetas y layout */
  </style>
</head>
<body>
  {% if bare %}
    {{ body|safe }}
  {% else %}
    <div class="app-shell">
      <aside class="sidebar">
        <!-- Sidebar dinamico segun el tipo de usuario -->
      </aside>
      <main class="content">
        <!-- Mensajes flash + contenido del modulo -->
        {{ body|safe }}
      </main>
    </div>
  {% endif %}

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    // Script para autocompletar precio sugerido segun material y unidad.
    const materialSelect = document.querySelector('[data-material-select]');
    const unitSelect = document.querySelector('[data-unit-select]');
    const priceInput = document.querySelector('[data-price-input]');
    const prices = {{ suggested_prices|tojson }};

    if (materialSelect && priceInput) {
      const updateSuggestedPrice = () => {
        const value = materialSelect.value;
        const unit = unitSelect ? unitSelect.value : 'kg';
        if (prices[value] && prices[value][unit] !== undefined) {
          priceInput.value = prices[value][unit];
        }
      };
      materialSelect.addEventListener('change', updateSuggestedPrice);
      if (unitSelect) unitSelect.addEventListener('change', updateSuggestedPrice);
      updateSuggestedPrice();
    }
  </script>
</body>
</html>
"""


def render_page(body: str, title: str, active: str = "", company: dict | None = None, bare: bool = False):
    """
    Renderiza una pagina completa usando la plantilla base.
    Cambia colores, logo y menu dependiendo si es superadmin o cliente.
    """
    if company:
        theme_color = company["primary_color"]
        theme_background = company.get("background") or "linear-gradient(135deg, #f8fafc, #eef2ff)"
        logo = company.get("logo") or company["name"][:2].upper()
        sidebar_title = company["name"]
        sidebar_subtitle = "Panel cliente"
        nav = client_nav()
    else:
        theme_color = "#111827"
        theme_background = "linear-gradient(135deg, #f8fafc, #e0f2fe)"
        logo = "CO"
        sidebar_title = APP_NAME
        sidebar_subtitle = COMPANY_NAME
        nav = superadmin_nav()

    return render_template_string(
        BASE_TEMPLATE,
        body=body,
        title=title,
        active=active,
        bare=bare,
        nav=nav,
        logo=logo,
        sidebar_title=sidebar_title,
        sidebar_subtitle=sidebar_subtitle,
        theme_color=theme_color,
        theme_background=theme_background,
        suggested_prices=SUGGESTED_PRICES,
    )


# -------------------------------------------------------------------
# MENUS DE NAVEGACION
# -------------------------------------------------------------------
def superadmin_nav() -> list[dict]:
    """Menu lateral del superadmin."""
    return [
        {"key": "dashboard", "label": "Dashboard", "icon": "bi-speedometer2", "href": url_for("super_dashboard")},
        {"key": "companies", "label": "Empresas", "icon": "bi-buildings", "href": url_for("super_companies")},
        {"key": "payments", "label": "Pagos", "icon": "bi-credit-card", "href": url_for("super_payments")},
        {"key": "stats", "label": "Estadisticas", "icon": "bi-graph-up-arrow", "href": url_for("super_stats")},
        {"key": "backups", "label": "Respaldos", "icon": "bi-database-check", "href": url_for("super_backups")},
    ]


def client_nav() -> list[dict]:
    """Menu lateral del cliente."""
    return [
        {"key": "dashboard", "label": "Dashboard", "icon": "bi-grid-1x2", "href": url_for("client_dashboard")},
        {"key": "purchases", "label": "Compras", "icon": "bi-bag-plus", "href": url_for("client_module", module="purchases")},
        {"key": "sales", "label": "Ventas", "icon": "bi-receipt", "href": url_for("client_module", module="sales")},
        {"key": "inventory", "label": "Inventario", "icon": "bi-box-seam", "href": url_for("client_module", module="inventory")},
        {"key": "customers", "label": "Clientes", "icon": "bi-people", "href": url_for("client_module", module="customers")},
        {"key": "notes", "label": "Notas", "icon": "bi-journal-text", "href": url_for("client_module", module="notes")},
        {"key": "routes", "label": "Rutas", "icon": "bi-truck", "href": url_for("client_module", module="routes")},
        {"key": "reports", "label": "Reportes", "icon": "bi-bar-chart", "href": url_for("client_reports")},
        {"key": "settings", "label": "Configuracion", "icon": "bi-sliders", "href": url_for("client_settings")},
    ]


# -------------------------------------------------------------------
# LOGIN Y CIERRE DE SESION
# -------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    """
    Pantalla principal de acceso.
    Valida:
    - codigo privado
    - acceso de superadmin
    - acceso de empresa cliente
    """
    if request.method == "POST":
        user = request.form.get("user", "").strip()
        password = request.form.get("password", "").strip()
        access_code = request.form.get("access_code", "").strip()
        data = load_data()

        # Primero valida el codigo maestro del sistema
        if access_code not in ACCESS_CODES:
            flash("Codigo de acceso incorrecto. Solicita el codigo a BCR Systems.", "danger")
            return redirect(url_for("login"))

        # Luego intenta login como superadmin
        if (user, password) in SUPERADMIN_ALIASES:
            session.clear()
            session["role"] = "superadmin"
            session["name"] = "Superadmin"
            return redirect(url_for("super_dashboard"))

        # Si no es superadmin, busca si coincide con una empresa cliente
        company = next((c for c in data["companies"] if c["user"] == user and c["password"] == password), None)
        if company:
            if not company["active"]:
                flash("Empresa suspendida. Contacta al administrador de CycleOS.", "danger")
                return redirect(url_for("login"))

            session.clear()
            session["role"] = "client"
            session["company_id"] = company["id"]
            session["name"] = company["name"]
            return redirect(url_for("client_dashboard"))

        flash("Usuario o contrasena incorrectos.", "danger")

    # HTML del login
    body = """
    <section class="login-shell">
      <div class="login-card p-4 p-md-5" style="max-width: 980px; width: 100%;">
        <div class="row g-4 align-items-center">
          <div class="col-lg-6">
            <span class="badge badge-soft mb-3">SaaS multiempresa</span>
            <h1 class="display-5 fw-bold mb-3">CycleOS</h1>
            <p class="lead text-secondary mb-4">
              Sistema empresarial para reciclaje, rutas, inventario, ventas,
              compras y control centralizado por BCR Systems.
            </p>
          </div>
          <div class="col-lg-6">
            <form method="post" class="p-4 bg-white rounded-4 border">
              <h2 class="h4 fw-bold mb-1">Iniciar sesion</h2>
              <label class="form-label">Codigo de acceso</label>
              <input class="form-control mb-3" name="access_code" required>
              <label class="form-label">Usuario</label>
              <input class="form-control mb-3" name="user" required>
              <label class="form-label">Contrasena</label>
              <input class="form-control mb-4" name="password" type="password" required>
              <button class="btn btn-brand w-100 py-2">Entrar</button>
            </form>
          </div>
        </div>
      </div>
    </section>
    """
    return render_page(body, "Login", bare=True)


@app.route("/logout")
def logout():
    """Cierra la sesion actual y redirige al login."""
    session.clear()
    flash("Sesion cerrada correctamente.", "info")
    return redirect(url_for("login"))


# -------------------------------------------------------------------
# PANEL PRINCIPAL DEL SUPERADMIN
# -------------------------------------------------------------------
@app.route("/superadmin")
@login_required("superadmin")
def super_dashboard():
    """
    Dashboard central del administrador.
    Muestra estadisticas globales del sistema.
    """
    data = load_data()
    stats = global_stats(data)

    body = render_template_string(
        """
        <section class="hero-strip mb-4">
          <div class="d-flex flex-wrap justify-content-between gap-3 align-items-center">
            <div>
              <p class="mb-1 opacity-75">Panel de control total</p>
              <h1 class="h2 fw-bold mb-0">Superadmin CycleOS</h1>
            </div>
            <a class="btn btn-light" href="{{ url_for('super_companies') }}">Crear empresa</a>
          </div>
        </section>
        <div class="row g-3 mb-4">
          {{ stat('Empresas', stats.companies, 'bi-buildings') }}
          {{ stat('Activas', stats.active, 'bi-check-circle') }}
          {{ stat('Suspendidas', stats.suspended, 'bi-pause-circle') }}
          {{ stat('Ganancia SaaS estimada', stats.estimated|money, 'bi-cash-coin') }}
        </div>
        """,
        stats=stats,
        companies=data["companies"],
        stat=stat_macro(),
    )
    return render_page(body, "Superadmin", "dashboard")


def stat_macro():
    """
    Devuelve una funcion que genera una tarjeta HTML de estadistica.
    Se usa para no repetir el mismo bloque visual varias veces.
    """
    return lambda label, value, icon: Markup(render_template_string(
        """
        <div class="col-sm-6 col-xl-3">
          <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <div class="text-secondary small">{{ label }}</div>
                <div class="h3 fw-bold mb-0">{{ value }}</div>
              </div>
              <div class="stat-icon"><i class="bi {{ icon }}"></i></div>
            </div>
          </div>
        </div>
        """,
        label=label,
        value=value,
        icon=icon,
    ))

