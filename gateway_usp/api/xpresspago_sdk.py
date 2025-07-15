# gateway_usp/api/xpresspago_sdk.py

import frappe
import requests
import json
from datetime import datetime
from cryptography.fernet import Fernet
import hashlib
import hmac
import base64

class XpresspagoSDK:
    def __init__(self, environment="SANDBOX", merchant_id=None, secret_key=None, terminal_id=None):
        """
        Inicializa el SDK de XpressPago
        
        Args:
            environment: SANDBOX o PRODUCTION
            merchant_id: ID del comerciante
            secret_key: Clave secreta para autenticación
            terminal_id: ID del terminal (opcional)
        """
        self.environment = environment
        self.merchant_id = merchant_id
        self.secret_key = secret_key
        self.terminal_id = terminal_id
        
        # URLs base según el ambiente
        self.base_urls = {
            "SANDBOX": "https://sandbox-api.xpresspago.com/v1",
            "PRODUCTION": "https://api.xpresspago.com/v1"
        }
        
        self.base_url = self.base_urls.get(environment, self.base_urls["SANDBOX"])
        self.culture = "es"  # Idioma por defecto
        
    def _generate_signature(self, payload):
        """Genera la firma HMAC para autenticación"""
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, endpoint, method="POST", data=None):
        """Realiza peticiones HTTP a la API de XpressPago"""
        url = f"{self.base_url}/{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "X-Merchant-ID": self.merchant_id,
            "X-Culture": self.culture
        }
        
        if data:
            headers["X-Signature"] = self._generate_signature(data)
            
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            frappe.log_error(f"Error en petición XpressPago: {str(e)}")
            raise Exception(f"Error de conexión con XpressPago: {str(e)}")

    # Agregar método mejorado para guardar customer con tarjetas
    def save_customer_with_card(self, customer_data):
        """Guarda un cliente con tarjeta de crédito"""
        payload = {
            "UniqueIdentifier": customer_data.get("unique_identifier"),
            "FirstName": customer_data.get("first_name"),
            "LastName": customer_data.get("last_name"),
            "Email": customer_data.get("email"),
            "Phone": customer_data.get("phone"),
            "Company": customer_data.get("company"),
            "CreditCards": customer_data.get("credit_cards", []),
            "CustomFields": customer_data.get("custom_fields", {})
        }
        
        return self._make_request("customer", "POST", payload)

class CustomerManager:
    """Gestor de clientes en XpressPago"""
    
    def __init__(self, sdk):
        self.sdk = sdk
    
    def create_customer(self, customer_data):
        """Crea un cliente en XpressPago"""
        payload = {
            "UniqueIdentifier": customer_data.get("unique_identifier"),
            "FirstName": customer_data.get("first_name"),
            "LastName": customer_data.get("last_name"),
            "Email": customer_data.get("email"),
            "Phone": customer_data.get("phone"),
            "Company": customer_data.get("company"),
            "CustomFields": customer_data.get("custom_fields", {})
        }
        
        return self.sdk._make_request("customer", "POST", payload)
    
    def search_customer(self, filters):
        """Busca un cliente en XpressPago"""
        payload = {
            "UniqueIdentifier": filters.get("unique_identifier"),
            "SearchOption": {
                "IncludeAll": True
            }
        }
        
        return self.sdk._make_request("customer/search", "POST", payload)
    
    def update_customer(self, customer_data):
        """Actualiza un cliente en XpressPago"""
        payload = {
            "UniqueIdentifier": customer_data.get("unique_identifier"),
            "FirstName": customer_data.get("first_name"),
            "LastName": customer_data.get("last_name"),
            "Email": customer_data.get("email"),
            "Phone": customer_data.get("phone"),
            "Status": customer_data.get("status", "ACTIVE")
        }
        
        return self.sdk._make_request("customer", "PUT", payload)

    # Mejorar la clase CustomerManager
    def save_customer(self, customer_data):
        """Guarda o actualiza un cliente (mejorado)"""
        payload = {
            "UniqueIdentifier": customer_data.get("unique_identifier"),
            "FirstName": customer_data.get("first_name"),
            "LastName": customer_data.get("last_name"),
            "Email": customer_data.get("email"),
            "Phone": customer_data.get("phone"),
            "Company": customer_data.get("company"),
            "CustomFields": customer_data.get("custom_fields", {})
        }
        
        # Agregar tarjetas si existen
        if customer_data.get("credit_cards"):
            payload["CreditCards"] = customer_data["credit_cards"]
        
        # Si ya existe CustomerToken, es una actualización
        if customer_data.get("CustomerToken"):
            payload["CustomerToken"] = customer_data["CustomerToken"]
        
        return self.sdk._make_request("customer", "POST", payload)

class TransactionManager:
    """Gestor de transacciones en XpressPago"""
    
    def __init__(self, sdk):
        self.sdk = sdk
    
    def process_sale(self, transaction_data):
        """Procesa una venta en XpressPago"""
        payload = {
            "Amount": transaction_data.get("amount"),
            "CustomerData": {
                "CustomerId": transaction_data.get("customer_id"),
                "CreditCards": [
                    {
                        "Token": transaction_data.get("card_token")
                    }
                ]
            },
            "OrderTrackingNumber": transaction_data.get("order_tracking_number"),
            "CustomerId": transaction_data.get("customer_id")
        }
        
        return self.sdk._make_request("transaction/sale", "POST", payload)
    
    def process_refund(self, refund_data):
        """Procesa un reembolso en XpressPago"""
        payload = {
            "Amount": refund_data.get("amount"),
            "TransactionId": refund_data.get("transaction_id"),
            "CustomerData": {
                "CustomerId": refund_data.get("customer_id")
            }
        }
        
        return self.sdk._make_request("transaction/refund", "POST", payload)
    
    def update_transaction_status(self, status_data):
        """Actualiza el estado de una transacción"""
        payload = {
            "TransactionId": status_data.get("transaction_id"),
            "ThirdPartyStatus": status_data.get("status"),
            "ThirdPartyDescription": status_data.get("description")
        }
        
        return self.sdk._make_request("transaction/status", "POST", payload)
    
    def search_transaction(self, filters):
        """Busca transacciones en XpressPago"""
        payload = {
            "CustomerId": filters.get("customer_id"),
            "DateCreated": {
                "Between": [
                    filters.get("date_from"),
                    filters.get("date_to")
                ]
            }
        }
        
        return self.sdk._make_request("transaction/search", "POST", payload)

# Función de inicialización del SDK
def get_xpresspago_sdk():
    """Obtiene una instancia configurada del SDK de XpressPago"""
    settings = frappe.get_single("USP Payment Gateway Settings")
    
    if not settings.is_enabled:
        frappe.throw("Gateway USP no está habilitado")
    
    return XpresspagoSDK(
        environment=settings.environment,
        merchant_id=settings.merchant_id,
        secret_key=settings.get_password("secret_key"),
        terminal_id=settings.terminal_id
    )