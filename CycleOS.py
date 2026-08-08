# Sistema Recicladora
from __future__ import annotations
#####/////-----ggggg
import json
import os
import shutil
from datetime import datetime, timedelta
from functools import wraps
from uuid import uuid4

from flask import (
    Flask,
    flash,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
from markupsafe import Markup


# CycleOS - Primera version funcional en un solo archivo.
# Desarrollado para BCR Systems como base academica de un SaaS multiempresa.
# Para una version de produccion se recomienda usar base de datos, hashing de
# contrasenas, variables de entorno, migraciones y despliegue con HTTPS.

APP_NAME = "CycleOS"
COMPANY_NAME = "BCR Systems"
DATA_FILE = "cycleos_data.json"
BACKUP_DIR = "cycleos_backups"

SUPERADMIN_USER = "SpAdmin"
SUPERADMIN_PASSWORD = "AdminBCR1718"
ACCESS_CODE = os.getenv("CYCLEOS_ACCESS_CODE", "BcrSystems2026")

KG_TO_LB = 2.20462

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

SUGGESTED_PRICES = {
    material: {"kg": price, "lb": round(price / KG_TO_LB, 2)}
    for material, price in SUGGESTED_PRICES_KG.items()
}


app = Flask(__name__)
app.secret_key = os.getenv("CYCLEOS_SECRET_KEY", "cycleos-dev-secret-change-me")


def money(value: float) -> str:
    return f"Q{float(value):,.2f}"


app.jinja_env.filters["money"] = money


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def uid() -> str:
    return uuid4().hex[:10]


def default_data() -> dict:
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


def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        data = default_data()
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def company_records(data: dict, company_id: str) -> dict:
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
    return float(weight) / KG_TO_LB if unit == "lb" else float(weight)


def find_company(data: dict, company_id: str) -> dict | None:
    return next((item for item in data["companies"] if item["id"] == company_id), None)


def calculate_totals(records: dict) -> dict:
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
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"cycleos_backup_{stamp}.json"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    save_data(data)
    shutil.copy(DATA_FILE, backup_path)
    data["backups"].append({"id": uid(), "date": now_text(), "file": backup_path, "reason": reason})
    save_data(data)
    return backup_path


def login_required(role: str | None = None):
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
    :root {
      --brand: {{ theme_color|default('#111827') }};
      --brand-soft: color-mix(in srgb, var(--brand), white 86%);
      --page-bg: {{ theme_background|default('linear-gradient(135deg, #f8fafc, #eef2ff)') }};
    }
    body {
      min-height: 100vh;
      background: var(--page-bg);
      color: #172033;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .login-shell {
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
      background:
        radial-gradient(circle at top left, color-mix(in srgb, var(--brand), transparent 70%), transparent 35%),
        linear-gradient(135deg, #f8fafc, #e0f2fe);
    }
    .login-card, .panel-card, .table-card {
      background: rgba(255, 255, 255, .88);
      border: 1px solid rgba(148, 163, 184, .22);
      border-radius: 18px;
      box-shadow: 0 22px 60px rgba(15, 23, 42, .10);
      backdrop-filter: blur(18px);
    }
    .app-shell {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      min-height: 100vh;
    }
    .sidebar {
      background: #0f172a;
      color: #e5e7eb;
      padding: 24px 18px;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
    }
    .brand-badge {
      width: 48px;
      height: 48px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      background: var(--brand);
      color: white;
      font-weight: 800;
      box-shadow: 0 12px 30px color-mix(in srgb, var(--brand), transparent 55%);
    }
    .nav-link-cycle {
      display: flex;
      gap: 11px;
      align-items: center;
      color: #cbd5e1;
      padding: 11px 13px;
      border-radius: 12px;
      text-decoration: none;
      transition: .18s ease;
      margin-bottom: 4px;
    }
    .nav-link-cycle:hover, .nav-link-cycle.active {
      background: rgba(255, 255, 255, .10);
      color: #fff;
      transform: translateX(3px);
    }
    .content {
      padding: 26px;
    }
    .hero-strip {
      background: linear-gradient(135deg, var(--brand), color-mix(in srgb, var(--brand), black 28%));
      color: white;
      border-radius: 22px;
      padding: 26px;
      box-shadow: 0 24px 60px color-mix(in srgb, var(--brand), transparent 72%);
    }
    .stat-card {
      border: 1px solid rgba(148, 163, 184, .20);
      border-radius: 18px;
      padding: 20px;
      background: rgba(255, 255, 255, .90);
      box-shadow: 0 16px 42px rgba(15, 23, 42, .08);
      transition: .2s ease;
      height: 100%;
    }
    .stat-card:hover { transform: translateY(-3px); }
    .stat-icon {
      width: 42px;
      height: 42px;
      border-radius: 13px;
      display: grid;
      place-items: center;
      background: var(--brand-soft);
      color: var(--brand);
      font-size: 1.25rem;
    }
    .btn-brand {
      --bs-btn-bg: var(--brand);
      --bs-btn-border-color: var(--brand);
      --bs-btn-hover-bg: color-mix(in srgb, var(--brand), black 12%);
      --bs-btn-hover-border-color: color-mix(in srgb, var(--brand), black 12%);
      color: white;
      border-radius: 12px;
    }
    .badge-soft {
      background: var(--brand-soft);
      color: var(--brand);
      border: 1px solid color-mix(in srgb, var(--brand), white 70%);
    }
    .form-control, .form-select {
      border-radius: 12px;
      border-color: #dbe3ef;
    }
    .module-title {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .module-title i { color: var(--brand); }
    .price-chip {
      border-radius: 999px;
      padding: 8px 12px;
      background: white;
      border: 1px solid #e2e8f0;
      font-size: .9rem;
    }
    @media (max-width: 920px) {
      .app-shell { grid-template-columns: 1fr; }
      .sidebar { position: static; height: auto; }
      .content { padding: 18px; }
    }
  </style>
</head>
<body>
  {% if bare %}
    {{ body|safe }}
  {% else %}
    <div class="app-shell">
      <aside class="sidebar">
        <div class="d-flex align-items-center gap-3 mb-4">
          <div class="brand-badge">{{ logo }}</div>
          <div>
            <div class="fw-bold text-white">{{ sidebar_title }}</div>
            <small class="text-secondary">{{ sidebar_subtitle }}</small>
          </div>
        </div>
        <nav>
          {% for item in nav %}
            <a class="nav-link-cycle {% if active == item.key %}active{% endif %}" href="{{ item.href }}">
              <i class="bi {{ item.icon }}"></i><span>{{ item.label }}</span>
            </a>
          {% endfor %}
        </nav>
        <div class="mt-4 pt-3 border-top border-secondary-subtle">
          <a class="nav-link-cycle" href="{{ url_for('logout') }}"><i class="bi bi-box-arrow-left"></i><span>Cerrar sesion</span></a>
        </div>
      </aside>
      <main class="content">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {{ body|safe }}
      </main>
    </div>
  {% endif %}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    const materialSelect = document.querySelector('[data-material-select]');
    const unitSelect = document.querySelector('[data-unit-select]');
    const priceInput = document.querySelector('[data-price-input]');
    const prices = {{ suggested_prices|tojson }};
    if (materialSelect && priceInput) {
      const updateSuggestedPrice = () => {
        const value = materialSelect.value;
        const unit = unitSelect ? unitSelect.value : 'kg';
        if (prices[value] && prices[value][unit] !== undefined) priceInput.value = prices[value][unit];
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


def superadmin_nav() -> list[dict]:
    return [
        {"key": "dashboard", "label": "Dashboard", "icon": "bi-speedometer2", "href": url_for("super_dashboard")},
        {"key": "companies", "label": "Empresas", "icon": "bi-buildings", "href": url_for("super_companies")},
        {"key": "payments", "label": "Pagos", "icon": "bi-credit-card", "href": url_for("super_payments")},
        {"key": "stats", "label": "Estadisticas", "icon": "bi-graph-up-arrow", "href": url_for("super_stats")},
        {"key": "backups", "label": "Respaldos", "icon": "bi-database-check", "href": url_for("super_backups")},
    ]


def client_nav() -> list[dict]:
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


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("user", "").strip()
        password = request.form.get("password", "").strip()
        access_code = request.form.get("access_code", "").strip()
        data = load_data()

        if access_code != ACCESS_CODE:
            flash("Codigo de acceso incorrecto. Solicita el codigo a BCR Systems.", "danger")
            return redirect(url_for("login"))

        if user == SUPERADMIN_USER and password == SUPERADMIN_PASSWORD:
            session.clear()
            session["role"] = "superadmin"
            session["name"] = "Superadmin"
            return redirect(url_for("super_dashboard"))

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

    body = """
    <section class="login-shell">
      <div class="login-card p-4 p-md-5" style="max-width: 980px; width: 100%;">
        <div class="row g-4 align-items-center">
          <div class="col-lg-6">
            <span class="badge badge-soft mb-3">SaaS multiempresa</span>
            <h1 class="display-5 fw-bold mb-3">CycleOS</h1>
            <p class="lead text-secondary mb-4">Sistema empresarial para reciclaje, rutas, inventario, ventas, compras y control centralizado por BCR Systems.</p>
            <div class="d-flex flex-wrap gap-2">
              <span class="price-chip"><i class="bi bi-shield-lock me-1"></i> Superadmin</span>
              <span class="price-chip"><i class="bi bi-buildings me-1"></i> Empresas independientes</span>
              <span class="price-chip"><i class="bi bi-database-check me-1"></i> Respaldos JSON</span>
            </div>
          </div>
          <div class="col-lg-6">
            <form method="post" class="p-4 bg-white rounded-4 border">
              <h2 class="h4 fw-bold mb-1">Iniciar sesion</h2>
              <p class="text-secondary small mb-4">Usa tu usuario, contrasena y codigo privado de BCR Systems.</p>
              <label class="form-label">Codigo de acceso</label>
              <input class="form-control mb-3" name="access_code" placeholder="Codigo privado" autocomplete="off" required>
              <label class="form-label">Usuario</label>
              <input class="form-control mb-3" name="user" placeholder="Usuario" autocomplete="username" required>
              <label class="form-label">Contrasena</label>
              <input class="form-control mb-4" name="password" type="password" placeholder="Contrasena" autocomplete="current-password" required>
              <button class="btn btn-brand w-100 py-2"><i class="bi bi-box-arrow-in-right me-1"></i> Entrar</button>
            </form>
          </div>
        </div>
      </div>
    </section>
    """
    return render_page(body, "Login", bare=True)


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesion cerrada correctamente.", "info")
    return redirect(url_for("login"))


@app.route("/superadmin")
@login_required("superadmin")
def super_dashboard():
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
            <a class="btn btn-light" href="{{ url_for('super_companies') }}"><i class="bi bi-plus-circle me-1"></i> Crear empresa</a>
          </div>
        </section>
        <div class="row g-3 mb-4">
          {{ stat('Empresas', stats.companies, 'bi-buildings') }}
          {{ stat('Activas', stats.active, 'bi-check-circle') }}
          {{ stat('Suspendidas', stats.suspended, 'bi-pause-circle') }}
          {{ stat('Ganancia SaaS estimada', stats.estimated|money, 'bi-cash-coin') }}
        </div>
        <div class="row g-3">
          <div class="col-lg-7">
            <div class="table-card p-4">
              <h2 class="h5 fw-bold mb-3">Empresas recientes</h2>
              <div class="table-responsive">
                <table class="table align-middle">
                  <thead><tr><th>Empresa</th><th>Usuario</th><th>Pago</th><th>Estado</th></tr></thead>
                  <tbody>
                    {% for company in companies %}
                    <tr>
                      <td class="fw-semibold">{{ company.name }}</td>
                      <td>{{ company.user }}</td>
                      <td>{{ company.payment_date }}</td>
                      <td>
                        {% if company.active %}
                          <span class="badge text-bg-success">Activa</span>
                        {% else %}
                          <span class="badge text-bg-warning">Suspendida</span>
                        {% endif %}
                      </td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="col-lg-5">
            <div class="panel-card p-4 h-100">
              <h2 class="h5 fw-bold mb-3">Resumen financiero global</h2>
              <div class="d-flex justify-content-between py-2 border-bottom"><span>Pagos recibidos</span><strong>{{ stats.revenue|money }}</strong></div>
              <div class="d-flex justify-content-between py-2 border-bottom"><span>Ventas empresas</span><strong>{{ stats.sales|money }}</strong></div>
              <div class="d-flex justify-content-between py-2 border-bottom"><span>Compras empresas</span><strong>{{ stats.purchases|money }}</strong></div>
              <div class="d-flex justify-content-between py-2"><span>Ganancia neta empresas</span><strong>{{ stats.profit|money }}</strong></div>
            </div>
          </div>
        </div>
        """,
        stats=stats,
        companies=data["companies"],
        stat=stat_macro(),
    )
    return render_page(body, "Superadmin", "dashboard")


def stat_macro():
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


@app.route("/superadmin/companies", methods=["GET", "POST"])
@login_required("superadmin")
def super_companies():
    data = load_data()
    if request.method == "POST":
        company_id = request.form["name"].lower().replace(" ", "-") + "-" + uid()[:4]
        company = {
            "id": company_id,
            "name": request.form["name"],
            "logo": request.form.get("logo") or request.form["name"][:2].upper(),
            "primary_color": request.form.get("primary_color") or "#0f766e",
            "background": f"linear-gradient(135deg, {request.form.get('primary_color') or '#0f766e'}18, #f8fafc)",
            "user": request.form["user"],
            "password": request.form["password"],
            "payment_date": request.form["payment_date"],
            "active": request.form.get("active") == "on",
            "created_at": today_text(),
        }
        data["companies"].append(company)
        company_records(data, company_id)
        create_backup(data, "empresa creada")
        flash("Empresa creada correctamente.", "success")
        return redirect(url_for("super_companies"))

    body = render_template_string(
        """
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
          <div>
            <h1 class="h3 fw-bold mb-1">Empresas registradas</h1>
            <p class="text-secondary mb-0">Activa, suspende y administra accesos de clientes.</p>
          </div>
        </div>
        <div class="row g-3">
          <div class="col-xl-4">
            <form method="post" class="panel-card p-4">
              <h2 class="h5 fw-bold mb-3">Crear empresa</h2>
              <input class="form-control mb-2" name="name" placeholder="Nombre de empresa" required>
              <input class="form-control mb-2" name="logo" placeholder="Logo o iniciales, ej. BCR">
              <input class="form-control mb-2" name="user" placeholder="Usuario" required>
              <input class="form-control mb-2" name="password" placeholder="Contrasena" required>
              <label class="form-label small text-secondary">Color principal</label>
              <input class="form-control form-control-color mb-2" name="primary_color" type="color" value="#0f766e">
              <label class="form-label small text-secondary">Fecha de pago</label>
              <input class="form-control mb-3" name="payment_date" type="date" value="{{ today }}" required>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" role="switch" name="active" checked>
                <label class="form-check-label">Empresa activa</label>
              </div>
              <button class="btn btn-brand w-100"><i class="bi bi-buildings me-1"></i> Guardar empresa</button>
            </form>
          </div>
          <div class="col-xl-8">
            <div class="table-card p-4">
              <div class="table-responsive">
                <table class="table align-middle">
                  <thead><tr><th>Empresa</th><th>Usuario</th><th>Pago</th><th>Estado</th><th class="text-end">Acciones</th></tr></thead>
                  <tbody>
                    {% for company in companies %}
                    <tr>
                      <td>
                        <div class="fw-semibold">{{ company.name }}</div>
                        <small class="text-secondary">{{ company.primary_color }}</small>
                      </td>
                      <td>{{ company.user }}</td>
                      <td>{{ company.payment_date }}</td>
                      <td>{{ 'Activa' if company.active else 'Suspendida' }}</td>
                      <td class="text-end">
                        <form class="d-inline" method="post" action="{{ url_for('toggle_company', company_id=company.id) }}">
                          <button class="btn btn-sm {{ 'btn-warning' if company.active else 'btn-success' }}">{{ 'Suspender' if company.active else 'Activar' }}</button>
                        </form>
                        <form class="d-inline" method="post" action="{{ url_for('reset_company_password', company_id=company.id) }}">
                          <button class="btn btn-sm btn-outline-secondary">Reiniciar clave</button>
                        </form>
                      </td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        """,
        companies=data["companies"],
        today=today_text(),
    )
    return render_page(body, "Empresas", "companies")


@app.post("/superadmin/company/<company_id>/toggle")
@login_required("superadmin")
def toggle_company(company_id: str):
    data = load_data()
    company = find_company(data, company_id)
    if company:
        company["active"] = not company["active"]
        create_backup(data, "estado de empresa actualizado")
        flash("Estado actualizado correctamente.", "success")
    return redirect(url_for("super_companies"))


@app.post("/superadmin/company/<company_id>/reset-password")
@login_required("superadmin")
def reset_company_password(company_id: str):
    data = load_data()
    company = find_company(data, company_id)
    if company:
        company["password"] = "1234"
        create_backup(data, "contrasena reiniciada")
        flash(f"Contrasena de {company['name']} reiniciada a 1234.", "info")
    return redirect(url_for("super_companies"))


@app.route("/superadmin/payments", methods=["GET", "POST"])
@login_required("superadmin")
def super_payments():
    data = load_data()
    if request.method == "POST":
        data["payments"].append(
            {
                "id": uid(),
                "company_id": request.form["company_id"],
                "date": request.form["date"],
                "amount": float(request.form["amount"]),
                "status": request.form["status"],
                "notes": request.form.get("notes", ""),
            }
        )
        company = find_company(data, request.form["company_id"])
        if company and request.form["status"] == "pagado":
            company["active"] = True
            company["payment_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        create_backup(data, "pago registrado")
        flash("Pago registrado correctamente.", "success")
        return redirect(url_for("super_payments"))

    body = render_template_string(
        """
        <h1 class="h3 fw-bold mb-4">Pagos</h1>
        <div class="row g-3">
          <div class="col-lg-4">
            <form method="post" class="panel-card p-4">
              <h2 class="h5 fw-bold mb-3">Registrar pago</h2>
              <select class="form-select mb-2" name="company_id" required>
                {% for company in companies %}
                  <option value="{{ company.id }}">{{ company.name }}</option>
                {% endfor %}
              </select>
              <input class="form-control mb-2" name="date" type="date" value="{{ today }}" required>
              <input class="form-control mb-2" name="amount" type="number" step="0.01" value="399" required>
              <select class="form-select mb-2" name="status">
                <option value="pagado">Pagado</option>
                <option value="pendiente">Pendiente</option>
              </select>
              <textarea class="form-control mb-3" name="notes" placeholder="Notas"></textarea>
              <button class="btn btn-brand w-100">Guardar pago</button>
            </form>
          </div>
          <div class="col-lg-8">
            <div class="table-card p-4">
              <table class="table align-middle">
                <thead><tr><th>Empresa</th><th>Fecha</th><th>Monto</th><th>Estado</th><th>Notas</th></tr></thead>
                <tbody>
                  {% for pay in payments %}
                  <tr>
                    <td>{{ names.get(pay.company_id, pay.company_id) }}</td>
                    <td>{{ pay.date }}</td>
                    <td>{{ pay.amount|money }}</td>
                    <td><span class="badge text-bg-{{ 'success' if pay.status == 'pagado' else 'warning' }}">{{ pay.status }}</span></td>
                    <td>{{ pay.notes }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        """,
        companies=data["companies"],
        payments=data["payments"],
        names={c["id"]: c["name"] for c in data["companies"]},
        today=today_text(),
    )
    return render_page(body, "Pagos", "payments")


@app.route("/superadmin/stats")
@login_required("superadmin")
def super_stats():
    data = load_data()
    stats = global_stats(data)
    body = render_template_string(
        """
        <h1 class="h3 fw-bold mb-4">Estadisticas del sistema</h1>
        <div class="row g-3 mb-4">
          {{ stat('Pagos recibidos', stats.revenue|money, 'bi-credit-card') }}
          {{ stat('Ganancia mensual estimada', stats.estimated|money, 'bi-graph-up') }}
          {{ stat('Ventas globales', stats.sales|money, 'bi-receipt') }}
          {{ stat('Ganancia neta global', stats.profit|money, 'bi-cash-stack') }}
        </div>
        <div class="table-card p-4">
          <h2 class="h5 fw-bold mb-3">Rendimiento por empresa</h2>
          <table class="table align-middle">
            <thead><tr><th>Empresa</th><th>Compras</th><th>Ventas</th><th>Ganancia</th><th>Rutas</th></tr></thead>
            <tbody>
              {% for row in rows %}
              <tr>
                <td class="fw-semibold">{{ row.name }}</td>
                <td>{{ row.totals.purchases|money }}</td>
                <td>{{ row.totals.sales|money }}</td>
                <td>{{ row.totals.profit|money }}</td>
                <td>{{ row.totals.routes }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        """,
        stats=stats,
        rows=[{"name": c["name"], "totals": calculate_totals(company_records(data, c["id"]))} for c in data["companies"]],
        stat=stat_macro(),
    )
    return render_page(body, "Estadisticas", "stats")


@app.route("/superadmin/backups", methods=["GET", "POST"])
@login_required("superadmin")
def super_backups():
    data = load_data()
    if request.method == "POST":
        path = create_backup(data, "respaldo manual")
        flash(f"Respaldo creado: {path}", "success")
        return redirect(url_for("super_backups"))
    body = render_template_string(
        """
        <div class="d-flex justify-content-between align-items-center mb-4">
          <h1 class="h3 fw-bold mb-0">Respaldos</h1>
          <form method="post"><button class="btn btn-brand"><i class="bi bi-database-check me-1"></i> Crear respaldo</button></form>
        </div>
        <div class="table-card p-4">
          <table class="table align-middle">
            <thead><tr><th>Fecha</th><th>Archivo</th><th>Motivo</th></tr></thead>
            <tbody>
              {% for backup in backups|reverse %}
              <tr><td>{{ backup.date }}</td><td>{{ backup.file }}</td><td>{{ backup.reason }}</td></tr>
              {% else %}
              <tr><td colspan="3" class="text-secondary">Aun no hay respaldos registrados.</td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        """,
        backups=data["backups"],
    )
    return render_page(body, "Respaldos", "backups")


def current_company() -> tuple[dict, dict, dict]:
    data = load_data()
    company = find_company(data, session["company_id"])
    if not company or not company["active"]:
        session.clear()
        flash("Tu empresa esta suspendida o no existe.", "danger")
        return data, None, None
    return data, company, company_records(data, company["id"])


@app.route("/app")
@login_required("client")
def client_dashboard():
    data, company, records = current_company()
    if not company:
        return redirect(url_for("login"))
    totals = calculate_totals(records)
    body = render_template_string(
        """
        <section class="hero-strip mb-4">
          <div class="d-flex flex-wrap justify-content-between gap-3 align-items-center">
            <div>
              <p class="mb-1 opacity-75">Panel independiente</p>
              <h1 class="h2 fw-bold mb-0">{{ company.name }}</h1>
            </div>
            <span class="btn btn-light disabled">Proximo pago: {{ company.payment_date }}</span>
          </div>
        </section>
        <div class="row g-3 mb-4">
          {{ stat('Compras', totals.purchases|money, 'bi-bag-plus') }}
          {{ stat('Ventas', totals.sales|money, 'bi-receipt') }}
          {{ stat('Ganancia neta', totals.profit|money, 'bi-cash-coin') }}
          {{ stat('Inventario kg eq.', totals.inventory_weight|round(2), 'bi-box-seam') }}
        </div>
        <div class="row g-3">
          <div class="col-lg-7">
            <div class="table-card p-4">
              <h2 class="h5 fw-bold mb-3">Rutas activas</h2>
              <table class="table align-middle">
                <thead><tr><th>Cliente</th><th>Material</th><th>Peso</th><th>Estado</th></tr></thead>
                <tbody>
                  {% for route in records.routes %}
                  <tr>
                    <td>{{ route.customer }}</td><td>{{ route.material }}</td><td>{{ route.weight }} {{ route.get('unit', 'kg') }}</td>
                    <td><span class="badge text-bg-info">{{ route.status }}</span></td>
                  </tr>
                  {% else %}
                  <tr><td colspan="4" class="text-secondary">Sin rutas registradas.</td></tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
          <div class="col-lg-5">
            <div class="panel-card p-4 h-100">
              <h2 class="h5 fw-bold mb-3">Precios sugeridos</h2>
              {% for material, price in prices.items() %}
                <div class="d-flex justify-content-between py-2 border-bottom">
                  <span class="text-capitalize">{{ material }}</span><strong>{{ price.kg|money }} / kg - {{ price.lb|money }} / lb</strong>
                </div>
              {% endfor %}
            </div>
          </div>
        </div>
        """,
        company=company,
        records=records,
        totals=totals,
        prices=SUGGESTED_PRICES,
        stat=stat_macro(),
    )
    return render_page(body, "Dashboard", "dashboard", company)


MODULES = {
    "purchases": {"title": "Compras", "icon": "bi-bag-plus"},
    "sales": {"title": "Ventas", "icon": "bi-receipt"},
    "inventory": {"title": "Inventario", "icon": "bi-box-seam"},
    "customers": {"title": "Clientes", "icon": "bi-people"},
    "notes": {"title": "Notas", "icon": "bi-journal-text"},
    "routes": {"title": "Rutas", "icon": "bi-truck"},
}


@app.route("/app/<module>", methods=["GET", "POST"])
@login_required("client")
def client_module(module: str):
    if module not in MODULES:
        return redirect(url_for("client_dashboard"))
    data, company, records = current_company()
    if not company:
        return redirect(url_for("login"))

    if request.method == "POST":
        save_module_record(records, module, request.form)
        create_backup(data, f"{module} actualizado")
        flash("Registro guardado correctamente.", "success")
        return redirect(url_for("client_module", module=module))

    body = render_template_string(
        """
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
          <div class="module-title">
            <i class="bi {{ meta.icon }} fs-3"></i>
            <div>
              <h1 class="h3 fw-bold mb-0">{{ meta.title }}</h1>
              <p class="text-secondary mb-0">Datos privados de {{ company.name }}.</p>
            </div>
          </div>
        </div>
        <div class="row g-3">
          <div class="col-xl-4">
            <form method="post" class="panel-card p-4">
              <h2 class="h5 fw-bold mb-3">Nuevo registro</h2>
              {{ form|safe }}
              <button class="btn btn-brand w-100 mt-2">Guardar</button>
            </form>
          </div>
          <div class="col-xl-8">
            <div class="table-card p-4">
              {{ table|safe }}
            </div>
          </div>
        </div>
        """,
        meta=MODULES[module],
        company=company,
        form=module_form(module),
        table=module_table(module, records[module]),
    )
    return render_page(body, MODULES[module]["title"], module, company)


def module_form(module: str) -> str:
    material_options = "".join(
        f"<option value='{m}'>{m.title()} - kg {money(p['kg'])} / lb {money(p['lb'])}</option>"
        for m, p in SUGGESTED_PRICES.items()
    )
    unit_options = """
        <select class="form-select mb-2" name="unit" data-unit-select required>
          <option value="kg">Kilogramos (kg)</option>
          <option value="lb">Libras (lb)</option>
        </select>
    """
    if module in ("purchases", "sales"):
        person = "supplier" if module == "purchases" else "customer"
        label = "Proveedor" if module == "purchases" else "Cliente"
        return f"""
        <input class="form-control mb-2" name="date" type="date" value="{today_text()}" required>
        <select class="form-select mb-2" name="material" data-material-select required>{material_options}</select>
        <input class="form-control mb-2" name="weight" type="number" step="0.01" placeholder="Peso" required>
        {unit_options}
        <input class="form-control mb-2" name="price" type="number" step="0.01" placeholder="Precio por unidad editable" data-price-input required>
        <input class="form-control mb-2" name="{person}" placeholder="{label}" required>
        """
    if module == "inventory":
        return f"""
        <select class="form-select mb-2" name="material" required>{material_options}</select>
        <input class="form-control mb-2" name="weight" type="number" step="0.01" placeholder="Peso disponible" required>
        {unit_options}
        <input class="form-control mb-2" name="location" placeholder="Ubicacion / bodega" required>
        """
    if module == "customers":
        return """
        <input class="form-control mb-2" name="name" placeholder="Nombre" required>
        <input class="form-control mb-2" name="phone" placeholder="Telefono" required>
        <input class="form-control mb-2" name="address" placeholder="Direccion" required>
        <input class="form-control mb-2" name="material" placeholder="Material frecuente" required>
        <textarea class="form-control mb-2" name="notes" placeholder="Notas"></textarea>
        """
    if module == "routes":
        return f"""
        <input class="form-control mb-2" name="customer" placeholder="Cliente" required>
        <input class="form-control mb-2" name="address" placeholder="Direccion" required>
        <select class="form-select mb-2" name="material" required>{material_options}</select>
        <input class="form-control mb-2" name="weight" type="number" step="0.01" placeholder="Peso" required>
        {unit_options}
        <input class="form-control mb-2" name="driver" placeholder="Conductor" required>
        <select class="form-select mb-2" name="status">
          <option value="pendiente">Pendiente</option>
          <option value="en camino">En camino</option>
          <option value="entregado">Entregado</option>
        </select>
        """
    return """
    <input class="form-control mb-2" name="date" type="date" required>
    <input class="form-control mb-2" name="title" placeholder="Titulo" required>
    <textarea class="form-control mb-2" name="body" placeholder="Nota" required></textarea>
    """


def save_module_record(records: dict, module: str, form) -> None:
    item = {"id": uid()}
    if module in ("purchases", "sales"):
        item.update(
            {
                "date": form["date"],
                "material": form["material"],
                "weight": float(form["weight"]),
                "unit": form.get("unit", "kg"),
                "price": float(form["price"]),
                "supplier" if module == "purchases" else "customer": form.get("supplier") or form.get("customer"),
            }
        )
        # El inventario se actualiza automaticamente al comprar o vender.
        adjust_inventory(records, item["material"], item["unit"], item["weight"] if module == "purchases" else -item["weight"])
    elif module == "inventory":
        item.update(
            {
                "material": form["material"],
                "weight": float(form["weight"]),
                "unit": form.get("unit", "kg"),
                "location": form["location"],
            }
        )
    elif module == "customers":
        item.update(
            {
                "name": form["name"],
                "phone": form["phone"],
                "address": form["address"],
                "material": form["material"],
                "notes": form.get("notes", ""),
            }
        )
    elif module == "routes":
        item.update(
            {
                "customer": form["customer"],
                "address": form["address"],
                "material": form["material"],
                "weight": float(form["weight"]),
                "unit": form.get("unit", "kg"),
                "driver": form["driver"],
                "status": form["status"],
            }
        )
    elif module == "notes":
        item.update({"date": form["date"], "title": form["title"], "body": form["body"]})
    records[module].append(item)


def adjust_inventory(records: dict, material: str, unit: str, weight_delta: float) -> None:
    item = next(
        (row for row in records["inventory"] if row["material"] == material and row.get("unit", "kg") == unit),
        None,
    )
    if item:
        item["weight"] = max(0, float(item["weight"]) + weight_delta)
    else:
        records["inventory"].append(
            {"id": uid(), "material": material, "weight": max(0, weight_delta), "unit": unit, "location": "General"}
        )


def module_table(module: str, items: list[dict]) -> str:
    if not items:
        return '<p class="text-secondary mb-0">Aun no hay registros en este modulo.</p>'
    headers = {
        "purchases": ["Fecha", "Material", "Peso", "Precio", "Proveedor", "Total"],
        "sales": ["Fecha", "Material", "Peso", "Precio", "Cliente", "Total"],
        "inventory": ["Material", "Peso", "Ubicacion"],
        "customers": ["Nombre", "Telefono", "Direccion", "Material", "Notas"],
        "routes": ["Cliente", "Direccion", "Material", "Peso", "Conductor", "Estado"],
        "notes": ["Fecha", "Titulo", "Nota"],
    }[module]
    rows = ""
    for item in reversed(items):
        if module in ("purchases", "sales"):
            person = item.get("supplier") or item.get("customer")
            total = float(item["weight"]) * float(item["price"])
            unit = item.get("unit", "kg")
            cells = [
                item["date"],
                item["material"],
                f"{item['weight']} {unit}",
                f"{money(item['price'])} / {unit}",
                person,
                money(total),
            ]
        elif module == "inventory":
            cells = [item["material"], f"{item['weight']} {item.get('unit', 'kg')}", item["location"]]
        elif module == "customers":
            cells = [item["name"], item["phone"], item["address"], item["material"], item["notes"]]
        elif module == "routes":
            cells = [
                item["customer"],
                item["address"],
                item["material"],
                f"{item['weight']} {item.get('unit', 'kg')}",
                item["driver"],
                item["status"],
            ]
        else:
            cells = [item["date"], item["title"], item["body"]]
        rows += "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"
    return f"""
    <div class="table-responsive">
      <table class="table align-middle">
        <thead><tr>{''.join(f'<th>{h}</th>' for h in headers)}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


@app.route("/app/reports")
@login_required("client")
def client_reports():
    data, company, records = current_company()
    if not company:
        return redirect(url_for("login"))
    totals = calculate_totals(records)
    body = render_template_string(
        """
        <h1 class="h3 fw-bold mb-4">Reportes y ganancias</h1>
        <div class="row g-3 mb-4">
          {{ stat('Compras totales', totals.purchases|money, 'bi-bag-plus') }}
          {{ stat('Ventas totales', totals.sales|money, 'bi-receipt') }}
          {{ stat('Ganancia neta', totals.profit|money, 'bi-cash-stack') }}
          {{ stat('Clientes', totals.customers, 'bi-people') }}
        </div>
        <div class="panel-card p-4">
          <h2 class="h5 fw-bold mb-3">Lectura rapida</h2>
          <p class="mb-0 text-secondary">
            CycleOS calcula automaticamente compras, ventas y ganancias netas usando el peso por precio de cada registro.
            Los respaldos se generan al guardar cambios importantes.
          </p>
        </div>
        """,
        totals=totals,
        stat=stat_macro(),
    )
    return render_page(body, "Reportes", "reports", company)


@app.route("/app/settings", methods=["GET", "POST"])
@login_required("client")
def client_settings():
    data, company, records = current_company()
    if not company:
        return redirect(url_for("login"))
    if request.method == "POST":
        company["name"] = request.form["name"]
        company["logo"] = request.form["logo"]
        company["primary_color"] = request.form["primary_color"]
        company["background"] = f"linear-gradient(135deg, {company['primary_color']}18, #f8fafc)"
        if request.form.get("password"):
            company["password"] = request.form["password"]
        create_backup(data, "configuracion de empresa")
        flash("Configuracion actualizada.", "success")
        return redirect(url_for("client_settings"))
    body = render_template_string(
        """
        <h1 class="h3 fw-bold mb-4">Configuracion</h1>
        <form method="post" class="panel-card p-4" style="max-width: 720px;">
          <label class="form-label">Nombre</label>
          <input class="form-control mb-3" name="name" value="{{ company.name }}" required>
          <label class="form-label">Logo / iniciales</label>
          <input class="form-control mb-3" name="logo" value="{{ company.logo }}" required>
          <label class="form-label">Color principal</label>
          <input class="form-control form-control-color mb-3" name="primary_color" type="color" value="{{ company.primary_color }}">
          <label class="form-label">Nueva contrasena</label>
          <input class="form-control mb-3" name="password" placeholder="Dejar vacio para conservar la actual">
          <button class="btn btn-brand">Guardar apariencia</button>
        </form>
        """,
        company=company,
    )
    return render_page(body, "Configuracion", "settings", company)


if __name__ == "__main__":
    load_data()
    print("CycleOS listo.")
    print("Credenciales protegidas. Inicia sesion con tus datos privados.")
    print("Red local: http://TU-IP-LOCAL:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
