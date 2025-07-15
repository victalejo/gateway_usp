# gateway_usp/templates/pages/test_connectivity.py

import frappe
from frappe.utils import get_url

def get_context(context):
    """Configuración del contexto para la página de pruebas de conectividad"""
    
    # Verificar permisos básicos
    if frappe.session.user == "Guest":
        frappe.throw("Acceso denegado. Debe iniciar sesión para acceder a las pruebas de conectividad.")
    
    # Verificar que el gateway esté disponible
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        context.gateway_enabled = settings.is_enabled
        context.environment = settings.environment
        context.use_mock = settings.get('use_mock_mode', False)
    except:
        context.gateway_enabled = False
        context.environment = "No configurado"
        context.use_mock = False
    
    # Configurar metadatos de la página
    context.page_title = "USP Gateway - Pruebas de Conectividad"
    context.description = "Herramienta de diagnóstico para probar la conectividad con USP Gateway basado en documentación CROEM API Token v6.5"
    
    # Información del sistema
    context.system_info = {
        "site_url": get_url(),
        "user": frappe.session.user,
        "timestamp": frappe.utils.now()
    }
    
    # Configurar breadcrumbs
    context.parents = [
        {
            "name": "Inicio",
            "route": "/"
        },
        {
            "name": "USP Gateway",
            "route": "/app/usp-payment-gateway-settings"
        }
    ]
    
    return context 