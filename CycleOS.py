# -------------------------------------------------------------------
# MODULOS DEL SUPERADMIN
# -------------------------------------------------------------------

@app.route("/superadmin/companies", methods=["GET", "POST"])
@login_required("superadmin")
def super_companies():
    # Carga toda la data del sistema
    data = load_data()

    # Si enviaron el formulario, crea una nueva empresa
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

        # Agrega la empresa y crea su estructura base de registros
        data["companies"].append(company)
        company_records(data, company_id)

        # Guarda respaldo para dejar trazabilidad
        create_backup(data, "empresa creada")
        flash("Empresa creada correctamente.", "success")
        return redirect(url_for("super_companies"))

    # Si es GET, renderiza la pantalla de empresas
    body = render_template_string("... HTML de empresas ...", companies=data["companies"], today=today_text())
    return render_page(body, "Empresas", "companies")


@app.post("/superadmin/company/<company_id>/toggle")
@login_required("superadmin")
def toggle_company(company_id: str):
    # Activa o suspende una empresa
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
    # Reinicia la contraseña a un valor por defecto
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
    # Administra pagos de las empresas cliente
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

        # Si el pago fue exitoso, reactiva la empresa y mueve la fecha del próximo pago
        company = find_company(data, request.form["company_id"])
        if company and request.form["status"] == "pagado":
            company["active"] = True
            company["payment_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        create_backup(data, "pago registrado")
        flash("Pago registrado correctamente.", "success")
        return redirect(url_for("super_payments"))

    body = render_template_string("... HTML de pagos ...")
    return render_page(body, "Pagos", "payments")


@app.route("/superadmin/stats")
@login_required("superadmin")
def super_stats():
    # Muestra estadísticas globales del sistema
    data = load_data()
    stats = global_stats(data)

    body = render_template_string(
        "... HTML de estadisticas ...",
        stats=stats,
        rows=[{"name": c["name"], "totals": calculate_totals(company_records(data, c["id"]))} for c in data["companies"]],
        stat=stat_macro(),
    )
    return render_page(body, "Estadisticas", "stats")


@app.route("/superadmin/backups", methods=["GET", "POST"])
@login_required("superadmin")
def super_backups():
    # Permite listar y crear respaldos manualmente
    data = load_data()

    if request.method == "POST":
        path = create_backup(data, "respaldo manual")
        flash(f"Respaldo creado: {path}", "success")
        return redirect(url_for("super_backups"))

    body = render_template_string("... HTML de respaldos ...", backups=data["backups"])
    return render_page(body, "Respaldos", "backups")


# -------------------------------------------------------------------
# CONTEXTO DE LA EMPRESA ACTUAL
# -------------------------------------------------------------------

def current_company() -> tuple[dict, dict, dict]:
    # Obtiene la empresa de la sesión actual
    data = load_data()
    company = find_company(data, session["company_id"])

    # Si ya no existe o está suspendida, cierra sesión
    if not company or not company["active"]:
        session.clear()
        flash("Tu empresa esta suspendida o no existe.", "danger")
        return data, None, None

    return data, company, company_records(data, company["id"])


# -------------------------------------------------------------------
# DASHBOARD DEL CLIENTE
# -------------------------------------------------------------------

@app.route("/app")
@login_required("client")
def client_dashboard():
    # Panel principal de cada empresa cliente
    data, company, records = current_company()
    if not company:
        return redirect(url_for("login"))

    totals = calculate_totals(records)

    body = render_template_string(
        "... HTML dashboard cliente ...",
        company=company,
        records=records,
        totals=totals,
        prices=SUGGESTED_PRICES,
        stat=stat_macro(),
    )
    return render_page(body, "Dashboard", "dashboard", company)


# Diccionario que define los módulos disponibles del cliente
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
    # Valida que el módulo exista
    if module not in MODULES:
        return redirect(url_for("client_dashboard"))

    data, company, records = current_company()
    if not company:
        return redirect(url_for("login"))

    # Si enviaron formulario, guarda un nuevo registro del módulo
    if request.method == "POST":
        save_module_record(records, module, request.form)
        create_backup(data, f"{module} actualizado")
        flash("Registro guardado correctamente.", "success")
        return redirect(url_for("client_module", module=module))

    # Si es GET, muestra formulario + tabla del módulo
    body = render_template_string(
        "... HTML modulo cliente ...",
        meta=MODULES[module],
        company=company,
        form=module_form(module),
        table=module_table(module, records[module]),
    )
    return render_page(body, MODULES[module]["title"], module, company)


# -------------------------------------------------------------------
# FORMULARIOS DINAMICOS POR MODULO
# -------------------------------------------------------------------

def module_form(module: str) -> str:
    # Genera el HTML del formulario según el módulo
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

    # Cada módulo tiene campos distintos
    if module in ("purchases", "sales"):
        ...
    if module == "inventory":
        ...
    if module == "customers":
        ...
    if module == "routes":
        ...
    return "..."  # Caso notas


# -------------------------------------------------------------------
# GUARDADO DE REGISTROS
# -------------------------------------------------------------------

def save_module_record(records: dict, module: str, form) -> None:
    # Crea un registro nuevo y lo agrega al módulo correspondiente
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

        # Punto importante:
        # una compra suma inventario, una venta resta inventario
        adjust_inventory(
            records,
            item["material"],
            item["unit"],
            item["weight"] if module == "purchases" else -item["weight"]
        )

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
    # Busca si ya existe ese material en inventario
    item = next(
        (row for row in records["inventory"] if row["material"] == material and row.get("unit", "kg") == unit),
        None,
    )

    if item:
        # Actualiza el peso, pero nunca deja valores negativos
        item["weight"] = max(0, float(item["weight"]) + weight_delta)
    else:
        # Si no existe, crea una entrada nueva
        records["inventory"].append(
            {"id": uid(), "material": material, "weight": max(0, weight_delta), "unit": unit, "location": "General"}
        )


# -------------------------------------------------------------------
# TABLAS DINAMICAS
# -------------------------------------------------------------------

def module_table(module: str, items: list[dict]) -> str:
    # Genera una tabla HTML distinta según el módulo
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

    # Recorre los items y arma filas HTML
    rows = ""
    for item in reversed(items):
        ...
    return f"<table>...</table>"


# -------------------------------------------------------------------
# REPORTES Y CONFIGURACION DEL CLIENTE
# -------------------------------------------------------------------

@app.route("/app/reports")
@login_required("client")
def client_reports():
    # Muestra indicadores resumidos de la empresa
    data, company, records = current_company()
    if not company:
        return redirect(url_for("login"))

    totals = calculate_totals(records)

    body = render_template_string(
        "... HTML de reportes ...",
        totals=totals,
        stat=stat_macro(),
    )
    return render_page(body, "Reportes", "reports", company)


@app.route("/app/settings", methods=["GET", "POST"])
@login_required("client")
def client_settings():
    # Permite que la empresa cambie nombre, logo, color y contraseña
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

    body = render_template_string("... HTML configuracion ...", company=company)
    return render_page(body, "Configuracion", "settings", company)


# -------------------------------------------------------------------
# PUNTO DE ENTRADA DE LA APP
# -------------------------------------------------------------------

if __name__ == "__main__":
    # Asegura que exista el JSON antes de levantar la app
    load_data()

    print("CycleOS listo.")
    print("Credenciales protegidas. Inicia sesion con tus datos privados.")
    print("Red local: http://TU-IP-LOCAL:5000")

    # Ejecuta Flask en modo debug y accesible en la red local
    app.run(debug=True, host="0.0.0.0", port=5000)
