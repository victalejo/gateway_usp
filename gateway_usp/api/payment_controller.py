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