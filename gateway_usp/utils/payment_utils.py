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

def validate_card_number_luhn(card_number):
    """Valida número de tarjeta usando algoritmo de Luhn"""
    # Remover espacios y guiones
    cleaned = card_number.replace(" ", "").replace("-", "")
    
    # Debe contener solo números
    if not cleaned.isdigit():
        return False
    
    # Debe tener entre 13 y 19 dígitos
    if len(cleaned) < 13 or len(cleaned) > 19:
        return False
    
    # Algoritmo de Luhn
    total = 0
    should_double = False
    
    for i in range(len(cleaned) - 1, -1, -1):
        digit = int(cleaned[i])
        
        if should_double:
            digit *= 2
            if digit > 9:
                digit -= 9
        
        total += digit
        should_double = not should_double
    
    return total % 10 == 0

def get_card_type(card_number):
    """Detecta el tipo de tarjeta"""
    cleaned = card_number.replace(" ", "").replace("-", "")
    
    patterns = {
        'Visa': r'^4',
        'Mastercard': r'^5[1-5]',
        'American Express': r'^3[47]',
        'Discover': r'^6(?:011|5)',
        'Diners Club': r'^3[0689]',
        'JCB': r'^35'
    }
    
    import re
    for card_type, pattern in patterns.items():
        if re.match(pattern, cleaned):
            return card_type
    
    return "Unknown"

def mask_card_number(card_number):
    """Enmascara el número de tarjeta para mostrar solo los últimos 4 dígitos"""
    cleaned = card_number.replace(" ", "").replace("-", "")
    return "*" * (len(cleaned) - 4) + cleaned[-4:]

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

def get_valid_payment_request_type():
    """Obtiene el tipo de Payment Request válido según la configuración del sistema"""
    try:
        # Obtener las opciones del campo payment_request_type
        meta = frappe.get_meta("Payment Request")
        payment_type_field = meta.get_field("payment_request_type")
        
        if payment_type_field and payment_type_field.options:
            options = payment_type_field.options.split('\n')
            
            # Priorizar opciones conocidas
            if "Interior" in options:
                return "Interior"
            elif "Exterior" in options:
                return "Exterior"
            elif "Inbound" in options:
                return "Inbound"
            else:
                # Usar la primera opción disponible
                return options[0].strip()
        
        # Fallback por defecto
        return "Interior"
        
    except Exception as e:
        frappe.log_error(f"Error obteniendo payment_request_type: {str(e)}")
        return "Interior"  # Valor por defecto basado en el error

@frappe.whitelist()
def get_payment_request_type_options():
    """Obtiene las opciones disponibles para payment_request_type"""
    try:
        meta = frappe.get_meta("Payment Request")
        payment_type_field = meta.get_field("payment_request_type")
        
        if payment_type_field and payment_type_field.options:
            options = [opt.strip() for opt in payment_type_field.options.split('\n') if opt.strip()]
            return {
                "success": True,
                "options": options,
                "default": options[0] if options else None
            }
        
        return {
            "success": False,
            "message": "No se encontraron opciones para payment_request_type"
        }
        
    except Exception as e:
        frappe.log_error(f"Error obteniendo opciones payment_request_type: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def create_payment_request_with_usp(doc, amount, currency="USD"):
    """Crea un Payment Request con USP habilitado - MEJORADO"""
    try:
        # Validar parámetros
        if isinstance(doc, str):
            doc = frappe.get_doc("Sales Invoice", doc)
        
        # Convertir amount a float y validar
        amount = float(amount)
        validate_payment_amount(amount, currency)
        
        # Verificar que el usuario tenga permisos
        if not frappe.has_permission("Payment Request", "create"):
            frappe.throw("No tienes permisos para crear Payment Request")
        
        # Obtener opciones válidas para payment_request_type
        payment_request_type = get_valid_payment_request_type()
        
        # Crear Payment Request
        payment_request = frappe.get_doc({
            "doctype": "Payment Request",
            "payment_request_type": payment_request_type,
            "party_type": "Customer",
            "party": doc.customer,
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "currency": currency,
            "grand_total": amount,
            "usp_payment_method": 1,
            "payment_gateway": "USP Gateway",
            "email_to": doc.contact_email or ""
        })
        
        payment_request.insert(ignore_permissions=True)
        payment_request.submit()
        
        # NUEVO: Preparar datos para la URL de pago
        payment_url_data = {
            "name": payment_request.name,
            "amount": amount,
            "currency": currency,
            "customer": doc.customer,
            "reference_doctype": doc.doctype,
            "reference_docname": doc.name,
            "party": doc.customer,
            "grand_total": amount
        }
        
        # Agregar datos de la factura al Payment Request
        payment_request.payment_url_data = payment_url_data
        
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

@frappe.whitelist()
def debug_payment_data():
    """Función para depurar datos de pago"""
    try:
        # Obtener datos de la sesión actual
        debug_info = {
            "user": frappe.session.user,
            "route_options": frappe.local.form_dict,
            "timestamp": frappe.utils.now(),
            "session_data": frappe.session
        }
        
        frappe.log_error(
            json.dumps(debug_info, indent=2),
            "USP Payment Debug Info"
        )
        
        return debug_info
        
    except Exception as e:
        frappe.log_error(f"Error en debug_payment_data: {str(e)}")
        return {"error": str(e)}

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
        
        # Verificar opciones válidas de payment_request_type
        type_options = get_payment_request_type_options()
        if not type_options["success"]:
            return {"valid": False, "message": "Error verificando tipos de pago disponibles"}
        
        return {"valid": True, "message": "OK", "payment_types": type_options["options"]}
        
    except Exception as e:
        frappe.log_error(f"Error validando Payment Request: {str(e)}")
        return {"valid": False, "message": str(e)}