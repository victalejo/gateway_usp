from . import __version__ as app_version

app_name = "gateway_usp"
app_title = "Gateway USP"
app_publisher = "EduTech"
app_description = "Módulo de integración con pasarela de pagos XpressPago USP"
app_icon = "octicon octicon-credit-card"
app_color = "blue"
app_email = "victoralejocj@gmail.com"
app_license = "MIT"

# Documentos requeridos
required_apps = ["erpnext"]

# Hooks para DocTypes con carga condicional
doctype_js = {
    "Sales Invoice": "public/js/usp_payment_gateway.js",
    "Payment Request": "public/js/usp_payment_gateway.js"
}

# Assets que se cargan globalmente
app_include_js = [
    "usp_payment_gateway.bundle.js"
]

# Crear el bundle
app_include_css = [
    "usp_payment_gateway.bundle.css"
]

# Hooks para instalación
after_install = "gateway_usp.install.after_install"
before_uninstall = "gateway_usp.install.before_uninstall"

# Fixtures
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": {
            "name": ["in", [
                "Payment Request-usp_payment_method",
                "Payment Entry-usp_transaction_id",
                "Sales Invoice-usp_payment_gateway",
                "Customer-usp_customer_token"
            ]]
        }
    }
]

# Website
website_route_rules = [
    {"from_route": "/usp-payment/<path:path>", "to_route": "usp-payment"},
]

# Scheduler Events
scheduler_events = {
    "hourly": [
        "gateway_usp.api.payment_controller.sync_pending_transactions"
    ],
    "daily": [
        "gateway_usp.api.payment_controller.cleanup_old_transactions"
    ]
}

# Boot session para inicialización temprana
boot_session = "gateway_usp.boot.boot_session"