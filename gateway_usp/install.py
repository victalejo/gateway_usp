# gateway_usp/install.py

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """Configuración después de la instalación"""
    create_custom_fields_for_usp()
    create_payment_gateway_account()
    setup_default_settings()

def create_custom_fields_for_usp():
    """Crear campos personalizados para la integración USP"""
    custom_fields = {
        "Payment Request": [
            {
                "fieldname": "usp_payment_method",
                "label": "USP Payment Method",
                "fieldtype": "Check",
                "insert_after": "payment_gateway"
            }
        ],
        "Payment Entry": [
            {
                "fieldname": "usp_transaction_id",
                "label": "USP Transaction ID",
                "fieldtype": "Data",
                "insert_after": "reference_no"
            }
        ],
        "Sales Invoice": [
            {
                "fieldname": "usp_payment_gateway",
                "label": "Enable USP Payment",
                "fieldtype": "Check",
                "insert_after": "payment_terms_template"
            }
        ],
        "Customer": [
            {
                "fieldname": "usp_customer_token",
                "label": "USP Customer Token",
                "fieldtype": "Data",
                "insert_after": "customer_group"
            }
        ]
    }
    
    create_custom_fields(custom_fields)

def create_payment_gateway_account():
    """Crear cuenta de pasarela de pago"""
    if not frappe.db.exists("Payment Gateway Account", "USP Gateway"):
        gateway_account = frappe.get_doc({
            "doctype": "Payment Gateway Account",
            "payment_gateway": "USP Gateway",
            "payment_account": "USP Gateway - " + frappe.defaults.get_global_default("company"),
            "currency": "USD",
            "is_default": 1
        })
        gateway_account.insert()

def setup_default_settings():
    """Configurar ajustes por defecto"""
    if not frappe.db.exists("USP Payment Gateway Settings"):
        settings = frappe.get_doc({
            "doctype": "USP Payment Gateway Settings",
            "is_enabled": 0,
            "environment": "SANDBOX",
            "default_currency": "USD",
            "payment_timeout": 300,
            "auto_capture": 1
        })
        settings.insert()

def before_uninstall():
    """Limpieza antes de desinstalar"""
    # Eliminar campos personalizados
    frappe.db.sql("""
        DELETE FROM `tabCustom Field` 
        WHERE name IN (
            'Payment Request-usp_payment_method',
            'Payment Entry-usp_transaction_id',
            'Sales Invoice-usp_payment_gateway',
            'Customer-usp_customer_token'
        )
    """)
    
    frappe.db.commit()