# gateway_usp/boot.py

import frappe

def boot_session(bootinfo):
    """Configuración que se carga en cada sesión"""
    
    # Verificar si USP está habilitado
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        bootinfo.usp_gateway = {
            "enabled": settings.is_enabled,
            "environment": settings.environment,
            "currency": settings.default_currency
        }
    except:
        bootinfo.usp_gateway = {
            "enabled": False,
            "environment": "SANDBOX",
            "currency": "USD"
        } 