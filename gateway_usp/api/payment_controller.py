# gateway_usp/api/payment_controller.py

import frappe
from frappe import _
from frappe.utils import flt, now, get_url
import json
from .xpresspago_sdk import get_xpresspago_sdk, CustomerManager, TransactionManager

@frappe.whitelist()
def process_payment(payment_data):
    """
    Procesa un pago a través de XpressPago
    
    Args:
        payment_data: Datos del pago en formato JSON
    """
    try:
        # Validar datos de entrada
        if isinstance(payment_data, str):
            payment_data = json.loads(payment_data)
        
        # Obtener SDK configurado
        sdk = get_xpresspago_sdk()
        transaction_manager = TransactionManager(sdk)
        
        # Procesar el pago
        result = transaction_manager.process_sale({
            "amount": flt(payment_data.get("amount")),
            "customer_id": payment_data.get("customer_id"),
            "card_token": payment_data.get("card_token"),
            "order_tracking_number": payment_data.get("reference_docname")
        })
        
        # Crear registro de transacción
        transaction = frappe.get_doc({
            "doctype": "USP Transaction",
            "reference_doctype": payment_data.get("reference_doctype"),
            "reference_docname": payment_data.get("reference_docname"),
            "amount": flt(payment_data.get("amount")),
            "currency": payment_data.get("currency", "USD"),
            "customer": payment_data.get("customer"),
            "transaction_id": result.get("TransactionId"),
            "status": "Pending",
            "response_data": json.dumps(result)
        })
        transaction.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "transaction_id": result.get("TransactionId"),
            "status": result.get("Status"),
            "message": _("Pago procesado exitosamente")
        }
        
    except Exception as e:
        frappe.log_error(f"Error procesando pago USP: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": _("Error al procesar el pago")
        }

@frappe.whitelist()
def process_payment_with_new_card(payment_data):
    """
    Procesa un pago con una nueva tarjeta de crédito - MEJORADO
    
    Args:
        payment_data: Datos del pago incluyendo información de la nueva tarjeta
    """
    try:
        # Validar datos de entrada
        if isinstance(payment_data, str):
            payment_data = json.loads(payment_data)
        
        # Validar campos requeridos
        required_fields = ['amount', 'customer', 'card_data']
        for field in required_fields:
            if not payment_data.get(field):
                frappe.throw(f"Campo requerido faltante: {field}")
        
        # Validar amount específicamente
        amount = payment_data.get('amount')
        if not amount:
            frappe.throw("El campo 'amount' es requerido")
        
        try:
            amount = float(amount)
            if amount <= 0:
                frappe.throw("El monto debe ser mayor a cero")
        except (ValueError, TypeError):
            frappe.throw(f"Monto inválido: {amount}")
        
        # Log para debug
        frappe.log_error(
            f"Procesando pago USP - Amount: {amount}, Customer: {payment_data.get('customer')}, Currency: {payment_data.get('currency', 'USD')}",
            "USP Payment Debug"
        )
        
        card_data = payment_data.get('card_data')
        card_required_fields = ['card_number', 'cardholder_name', 'expiry_month', 'expiry_year', 'cvv']
        for field in card_required_fields:
            if not card_data.get(field):
                frappe.throw(f"Campo de tarjeta requerido faltante: {field}")
        
        # Validar monto
        from gateway_usp.utils.payment_utils import validate_payment_amount
        validate_payment_amount(amount, payment_data.get('currency', 'USD'))
        
        # Obtener SDK configurado
        sdk = get_xpresspago_sdk()
        customer_manager = CustomerManager(sdk)
        transaction_manager = TransactionManager(sdk)
        
        # 1. Buscar o crear cliente en XpressPago
        customer_response = _get_or_create_customer(customer_manager, payment_data.get('customer'))
        
        if not customer_response.get('success'):
            frappe.throw(f"Error con cliente: {customer_response.get('error')}")
        
        customer_token = customer_response.get('customer_token')
        
        # 2. Agregar tarjeta al cliente
        card_response = _add_card_to_customer(customer_manager, customer_token, card_data)
        
        if not card_response.get('success'):
            frappe.throw(f"Error agregando tarjeta: {card_response.get('error')}")
        
        card_token = card_response.get('card_token')
        
        # 3. Procesar el pago
        transaction_response = transaction_manager.process_sale({
            "amount": flt(amount),
            "customer_id": customer_token,
            "card_token": card_token,
            "order_tracking_number": payment_data.get("reference_docname")
        })
        
        # 4. Crear registro de transacción
        transaction = frappe.get_doc({
            "doctype": "USP Transaction",
            "reference_doctype": payment_data.get("reference_doctype"),
            "reference_docname": payment_data.get("reference_docname"),
            "amount": flt(amount),
            "currency": payment_data.get("currency", "USD"),
            "customer": payment_data.get("customer"),
            "transaction_id": transaction_response.get("TransactionId"),
            "status": "Pending",
            "payment_method": "Credit Card",
            "card_last_four": card_data.get("card_number")[-4:],
            "response_data": json.dumps(transaction_response)
        })
        transaction.insert(ignore_permissions=True)
        
        # 5. Log de auditoría
        from gateway_usp.utils.payment_utils import log_usp_transaction
        log_usp_transaction(
            "new_card_payment",
            {
                "customer": payment_data.get("customer"),
                "amount": amount,
                "card_last_four": card_data.get("card_number")[-4:]
            },
            transaction_response
        )
        
        return {
            "success": True,
            "transaction_id": transaction_response.get("TransactionId"),
            "status": transaction_response.get("Status"),
            "message": _("Pago procesado exitosamente con nueva tarjeta")
        }
        
    except Exception as e:
        frappe.log_error(f"Error procesando pago con nueva tarjeta: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": _("Error al procesar el pago con nueva tarjeta")
        }

def _get_or_create_customer(customer_manager, customer_name):
    """Obtiene o crea un cliente en XpressPago"""
    try:
        # Obtener datos del cliente desde ERPNext
        customer_doc = frappe.get_doc("Customer", customer_name)
        
        # Primero intentar buscar el cliente existente
        search_response = customer_manager.search_customer({
            "unique_identifier": customer_name
        })
        
        if search_response.get("success") and search_response.get("data"):
            return {
                "success": True,
                "customer_token": search_response["data"].get("CustomerToken"),
                "existing": True
            }
        
        # Si no existe, crear nuevo cliente
        from gateway_usp.utils.payment_utils import get_customer_usp_data
        customer_data = get_customer_usp_data(customer_name)
        
        create_response = customer_manager.create_customer(customer_data)
        
        if create_response.get("IsSuccess"):
            return {
                "success": True,
                "customer_token": create_response.get("CustomerToken"),
                "existing": False
            }
        else:
            return {
                "success": False,
                "error": create_response.get("ResponseMessage", "Error creando cliente")
            }
            
    except Exception as e:
        frappe.log_error(f"Error gestionando cliente USP: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def _add_card_to_customer(customer_manager, customer_token, card_data):
    """Agrega una tarjeta a un cliente en XpressPago"""
    try:
        # Preparar datos de la tarjeta según la documentación
        card_object = {
            "CardholderName": card_data.get("cardholder_name"),
            "Number": card_data.get("card_number").replace(" ", ""),
            "ExpirationMonth": card_data.get("expiry_month"),
            "ExpirationYear": card_data.get("expiry_year"),
            "CVV": card_data.get("cvv"),
            "Status": "Active"
        }
        
        # Crear objeto Customer con la tarjeta
        customer_update = {
            "CustomerToken": customer_token,
            "CreditCards": [card_object]
        }
        
        # Agregar tarjeta usando el customer manager
        card_response = customer_manager.save_customer(customer_update)
        
        if card_response.get("IsSuccess"):
            # Obtener el token de la tarjeta de la respuesta
            card_token = None
            if card_response.get("CreditCards"):
                card_token = card_response["CreditCards"][0].get("Token")
            
            return {
                "success": True,
                "card_token": card_token,
                "response": card_response
            }
        else:
            return {
                "success": False,
                "error": card_response.get("ResponseMessage", "Error agregando tarjeta")
            }
            
    except Exception as e:
        frappe.log_error(f"Error agregando tarjeta: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def validate_card_details(card_number, expiry_month, expiry_year, cvv):
    """Valida los datos de una tarjeta de crédito"""
    try:
        errors = []
        
        # Validar número de tarjeta
        cleaned_number = card_number.replace(" ", "").replace("-", "")
        if not cleaned_number.isdigit():
            errors.append("Número de tarjeta debe contener solo números")
        elif len(cleaned_number) < 13 or len(cleaned_number) > 19:
            errors.append("Número de tarjeta debe tener entre 13 y 19 dígitos")
        
        # Validar fecha de vencimiento
        current_year = frappe.utils.now_datetime().year
        current_month = frappe.utils.now_datetime().month
        
        exp_year = int(expiry_year)
        exp_month = int(expiry_month)
        
        if exp_year < current_year or (exp_year == current_year and exp_month < current_month):
            errors.append("Tarjeta vencida")
        
        # Validar CVV
        if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
            errors.append("CVV inválido")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
        
    except Exception as e:
        frappe.log_error(f"Error validando tarjeta: {str(e)}")
        return {
            "valid": False,
            "errors": [str(e)]
        }

@frappe.whitelist(allow_guest=True)
def webhook_handler():
    """
    Maneja webhooks de XpressPago para actualizar estados de transacciones
    """
    try:
        # Obtener datos del webhook
        data = frappe.local.form_dict
        
        # Validar firma del webhook
        if not _validate_webhook_signature(data):
            frappe.throw(_("Firma de webhook inválida"))
        
        # Procesar actualización de estado
        transaction_id = data.get("transaction_id")
        new_status = data.get("status")
        
        if transaction_id:
            transaction = frappe.get_doc("USP Transaction", 
                                       {"transaction_id": transaction_id})
            
            # Actualizar estado
            transaction.status = new_status
            transaction.webhook_data = json.dumps(data)
            transaction.save(ignore_permissions=True)
            
            # Actualizar documento relacionado
            _update_related_document(transaction, new_status)
            
        return {"status": "success"}
        
    except Exception as e:
        frappe.log_error(f"Error procesando webhook USP: {str(e)}")
        return {"status": "error", "message": str(e)}

def _validate_webhook_signature(data):
    """Valida la firma del webhook"""
    # Implementar validación de firma según documentación XpressPago
    return True  # Placeholder

def _update_related_document(transaction, status):
    """Actualiza el documento relacionado según el estado de la transacción"""
    if status == "Completed":
        # Marcar como pagado
        if transaction.reference_doctype == "Payment Request":
            payment_request = frappe.get_doc("Payment Request", 
                                           transaction.reference_docname)
            payment_request.flags.ignore_permissions = True
            payment_request.set_as_paid()
            
        elif transaction.reference_doctype == "Sales Invoice":
            # Crear Payment Entry
            _create_payment_entry(transaction)

def _create_payment_entry(transaction):
    """Crea un Payment Entry para la transacción completada"""
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    
    # Obtener la factura
    invoice = frappe.get_doc("Sales Invoice", transaction.reference_docname)
    
    # Crear Payment Entry
    payment_entry = get_payment_entry(invoice.doctype, invoice.name)
    payment_entry.paid_amount = transaction.amount
    payment_entry.received_amount = transaction.amount
    payment_entry.reference_no = transaction.transaction_id
    payment_entry.reference_date = now()
    payment_entry.mode_of_payment = "USP Gateway"
    
    payment_entry.flags.ignore_permissions = True
    payment_entry.submit()
    
    return payment_entry

@frappe.whitelist()
def get_customer_cards(customer):
    """Obtiene las tarjetas guardadas de un cliente"""
    try:
        sdk = get_xpresspago_sdk()
        customer_manager = CustomerManager(sdk)
        
        # Buscar cliente en XpressPago
        result = customer_manager.search_customer({
            "unique_identifier": customer
        })
        
        cards = []
        if result.get("success") and result.get("data"):
            customer_data = result["data"]
            if customer_data.get("CreditCards"):
                cards = [
                    {
                        "token": card.get("Token"),
                        "last_four": card.get("Number", "")[-4:],
                        "brand": card.get("Brand", ""),
                        "expiry": f"{card.get('ExpirationMonth')}/{card.get('ExpirationYear')}"
                    }
                    for card in customer_data["CreditCards"]
                    if card.get("Status") == "Active"
                ]
        
        return cards
        
    except Exception as e:
        frappe.log_error(f"Error obteniendo tarjetas: {str(e)}")
        return []

@frappe.whitelist()
def create_usp_customer(customer_data):
    """Crea un cliente en XpressPago"""
    try:
        sdk = get_xpresspago_sdk()
        customer_manager = CustomerManager(sdk)
        
        result = customer_manager.create_customer(customer_data)
        
        return {
            "success": True,
            "customer_token": result.get("CustomerToken"),
            "message": _("Cliente creado exitosamente en USP")
        }
        
    except Exception as e:
        frappe.log_error(f"Error creando cliente USP: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def sync_pending_transactions():
    """Sincronizar transacciones pendientes (ejecutado cada hora)"""
    try:
        # Obtener transacciones pendientes de más de 10 minutos
        pending_transactions = frappe.get_all(
            "USP Transaction",
            filters={
                "status": "Pending",
                "created_at": ["<", frappe.utils.add_minutes(frappe.utils.now(), -10)]
            },
            fields=["name", "transaction_id"]
        )
        
        for transaction in pending_transactions:
            # Consultar estado en XpressPago
            # Implementar lógica de sincronización
            pass
            
    except Exception as e:
        frappe.log_error(f"Error sincronizando transacciones: {str(e)}")

@frappe.whitelist()
def cleanup_old_transactions():
    """Limpiar transacciones antiguas (ejecutado diariamente)"""
    try:
        # Eliminar logs de transacciones de más de 90 días
        old_date = frappe.utils.add_days(frappe.utils.now(), -90)
        
        frappe.db.sql("""
            DELETE FROM `tabUSP Transaction`
            WHERE created_at < %s
            AND status IN ('Cancelled', 'Failed')
        """, (old_date,))
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Error limpiando transacciones: {str(e)}")