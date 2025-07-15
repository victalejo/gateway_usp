# gateway_usp/utils/payment_utils.py

import frappe
from frappe.utils import flt, cint, get_url
import json

def validate_payment_amount(amount, currency="USD"):
    """Valida el monto del pago"""
    if flt(amount) <= 0:
        frappe.throw("El monto del pago debe ser mayor a cero")
    
    # Validar límites según la moneda
    limits = {
        "USD": {"min": 0.50, "max": 50000},
        "EUR": {"min": 0.50, "max": 50000},
        "PEN": {"min": 2.00, "max": 200000}
    }
    
    if currency in limits:
        if flt(amount) < limits[currency]["min"]:
            frappe.throw(f"El monto mínimo para {currency} es {limits[currency]['min']}")
        if flt(amount) > limits[currency]["max"]:
            frappe.throw(f"El monto máximo para {currency} es {limits[currency]['max']}")

def get_customer_usp_data(customer_name):
    """Obtiene datos del cliente para USP"""
    customer = frappe.get_doc("Customer", customer_name)
    
    return {
        "unique_identifier": customer.name,
        "first_name": customer.customer_name.split()[0] if customer.customer_name else "",
        "last_name": " ".join(customer.customer_name.split()[1:]) if customer.customer_name else "",
        "email": customer.email_id or "",
        "phone": customer.mobile_no or "",
        "company": customer.customer_group or "",
        "custom_fields": {
            "customer_type": customer.customer_type,
            "territory": customer.territory
        }
    }

@frappe.whitelist()
def create_payment_request_with_usp(doc, amount, currency="USD"):
    """Crea un Payment Request con USP habilitado"""
    try:
        # Validar parámetros
        if isinstance(doc, str):
            doc = frappe.get_doc("Sales Invoice", doc)
        
        validate_payment_amount(amount, currency)
        
        # Verificar que el usuario tenga permisos
        if not frappe.has_permission("Payment Request", "create"):
            frappe.throw("No tienes permisos para crear Payment Request")
        
        payment_request = frappe.get_doc({
            "doctype": "Payment Request",
            "payment_request_type": "Inbound",
            "party_type": "Customer",
            "party": doc.customer,
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "currency": currency,
            "grand_total": flt(amount),
            "usp_payment_method": 1,
            "payment_gateway": "USP Gateway",
            "email_to": doc.contact_email or ""
        })
        
        payment_request.insert(ignore_permissions=True)
        payment_request.submit()
        
        return payment_request.as_dict()
        
    except Exception as e:
        frappe.log_error(f"Error creando Payment Request USP: {str(e)}")
        frappe.throw(f"Error creando Payment Request: {str(e)}")

def format_usp_response(response_data):
    """Formatea la respuesta de USP para mostrar al usuario"""
    if not response_data:
        return {}
    
    return {
        "transaction_id": response_data.get("TransactionId"),
        "status": response_data.get("Status"),
        "amount": response_data.get("Amount"),
        "currency": response_data.get("Currency"),
        "customer_token": response_data.get("CustomerToken"),
        "response_code": response_data.get("ResponseCode"),
        "response_message": response_data.get("ResponseMessage"),
        "is_success": response_data.get("IsSuccess", False)
    }

def get_webhook_url():
    """Obtiene la URL del webhook para USP"""
    site_url = get_url()
    return f"{site_url}/api/method/gateway_usp.api.payment_controller.webhook_handler"

def log_usp_transaction(transaction_type, data, response=None, error=None):
    """Log de transacciones USP para auditoría"""
    log_entry = {
        "timestamp": frappe.utils.now(),
        "transaction_type": transaction_type,
        "data": data,
        "response": response,
        "error": error,
        "user": frappe.session.user
    }
    
    frappe.log_error(
        message=json.dumps(log_entry, indent=2),
        title=f"USP Transaction - {transaction_type}"
    )

# Función helper para obtener settings de USP
@frappe.whitelist()
def get_usp_settings():
    """Obtiene las configuraciones de USP Gateway"""
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        return {
            "is_enabled": settings.is_enabled,
            "environment": settings.environment,
            "default_currency": settings.default_currency,
            "auto_capture": settings.auto_capture
        }
    except Exception as e:
        frappe.log_error(f"Error obteniendo settings USP: {str(e)}")
        return {"is_enabled": False}

# Función para validar que Payment Request puede usar USP
@frappe.whitelist()
def validate_payment_request_for_usp(payment_request_name):
    """Valida que un Payment Request pueda usar USP"""
    try:
        pr = frappe.get_doc("Payment Request", payment_request_name)
        
        # Verificar que esté pendiente
        if pr.status != "Requested":
            return {"valid": False, "message": "Payment Request no está pendiente"}
        
        # Verificar que tenga customer
        if not pr.party:
            return {"valid": False, "message": "Payment Request no tiene customer"}
        
        # Verificar que USP esté habilitado
        settings = frappe.get_single("USP Payment Gateway Settings")
        if not settings.is_enabled:
            return {"valid": False, "message": "USP Gateway no está habilitado"}
        
        return {"valid": True, "message": "OK"}
        
    except Exception as e:
        frappe.log_error(f"Error validando Payment Request: {str(e)}")
        return {"valid": False, "message": str(e)}