# gateway_usp/templates/pages/test_connectivity.py

import frappe

def get_context(context):
    """Configuración del contexto para la página de pruebas de conectividad"""
    
    # Verificar permisos (opcional - solo usuarios con sesión activa)
    if not frappe.session.user:
        frappe.throw("Acceso denegado. Debe iniciar sesión.")
    
    # Verificar que el gateway esté disponible
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        context.gateway_enabled = settings.is_enabled
        context.environment = settings.environment
    except:
        context.gateway_enabled = False
        context.environment = "No configurado"
    
    # Configurar metadatos de la página
    context.page_title = "USP Gateway - Pruebas de Conectividad"
    context.description = "Herramienta de diagnóstico para probar la conectividad con USP Gateway basado en documentación CROEM API Token v6.5"
    
    # Incluir scripts de Frappe necesarios
    context.include_js = [
        "assets/frappe/js/frappe.js",
        "assets/frappe/js/frappe-web.js"
    ]
    
    # Configurar breadcrumbs
    context.parents = [
        {
            "name": "Inicio",
            "route": "/"
        },
        {
            "name": "USP Gateway",
            "route": "#"
        }
    ]
    
    return context 