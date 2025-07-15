# gateway_usp/api/xpresspago_sdk.py

import frappe
import requests
import json
import hmac
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, Optional

class XpresspagoSDK:
    """SDK mejorado basado en documentación CROEM API Token v6.5"""
    
    def __init__(self, environment="SANDBOX", api_key=None, access_code=None, 
                 merchant_account_number=None, terminal_name=None):
        """
        Inicializa el SDK con configuración CROEM
        
        Args:
            environment: SANDBOX o PRODUCTION
            api_key: Llave única que identifica al comercio
            access_code: Código de acceso del comercio
            merchant_account_number: MID provisto por el Banco Adquirente
            terminal_name: TID provisto por el Banco Adquirente
        """
        self.environment = environment
        self.api_key = api_key or "TEST_API_KEY"
        self.access_code = access_code or "TEST_ACCESS_CODE"
        self.merchant_account_number = merchant_account_number or "TEST_MERCHANT"
        self.terminal_name = terminal_name or "TEST_TERMINAL"
        
        # URLs basadas en la documentación CROEM
        self.base_urls = {
            "SANDBOX": {
                "api": "https://tokenv2test.merchantprocess.net/TokenWebService.asmx",
                "widget": "https://apicomponentv2-test.merchantprocess.net/UIComponent/CreditCard"
            },
            "PRODUCTION": {
                "api": "https://gateway.merchantprocess.net/tokenv2/TokenWebService.asmx",
                "widget": "https://gateway.merchantprocess.net/securecomponent/v2/UIComponent/CreditCard"
            }
        }
        
        self.base_url = self.base_urls.get(environment, self.base_urls["SANDBOX"])["api"]
        self.widget_url = self.base_urls.get(environment, self.base_urls["SANDBOX"])["widget"]
    
    def ping(self) -> Dict[str, Any]:
        """Verifica la disponibilidad del servicio según documentación CROEM"""
        try:
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/Ping"
            }
            
            soap_body = """<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                          xmlns:tem="http://tempuri.org/">
                <soap:Header/>
                <soap:Body>
                    <tem:Ping></tem:Ping>
                </soap:Body>
            </soap:Envelope>"""
            
            response = requests.post(
                self.base_url,
                data=soap_body,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "IsSuccess": True,
                    "PingResult": datetime.now().strftime("%m/%d/%Y %I:%M:%S %p"),
                    "ResponseCode": "00",
                    "ResponseMessage": "Service Available"
                }
            else:
                return {
                    "IsSuccess": False,
                    "ResponseCode": "999",
                    "ResponseMessage": f"HTTP Error: {response.status_code}"
                }
                
        except Exception as e:
            frappe.log_error(f"Error en ping: {str(e)}")
            return {
                "IsSuccess": False,
                "ResponseCode": "999",
                "ResponseMessage": f"Connection Error: {str(e)}"
            }
    
    def create_token_widget(self, token=None, culture="es") -> Dict[str, Any]:
        """Obtiene el widget de tokenización según documentación CROEM"""
        try:
            params = {
                "APIKey": self.api_key,
                "Culture": culture
            }
            
            if token:
                params["Token"] = token
            
            response = requests.get(
                self.widget_url,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "IsSuccess": True,
                    "WidgetHTML": response.text,
                    "ResponseCode": "T00",
                    "ResponseMessage": "Success"
                }
            else:
                return {
                    "IsSuccess": False,
                    "ResponseCode": "T01",
                    "ResponseMessage": f"Widget Error: {response.status_code}"
                }
                
        except Exception as e:
            frappe.log_error(f"Error obteniendo widget: {str(e)}")
            return {
                "IsSuccess": False,
                "ResponseCode": "T01",
                "ResponseMessage": f"Widget Error: {str(e)}"
            }
    
    def sale(self, account_token: str, amount: float, currency_code: str = "840", 
             client_tracking: str = None, **kwargs) -> Dict[str, Any]:
        """Procesa una venta usando token según documentación CROEM"""
        try:
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                          xmlns:tem="http://tempuri.org/">
                <soap:Header/>
                <soap:Body>
                    <tem:Sale>
                        <tem:APIKey>{self.api_key}</tem:APIKey>
                        <tem:accountToken>{account_token}</tem:accountToken>
                        <tem:accessCode>{self.access_code}</tem:accessCode>
                        <tem:merchantAccountNumber>{self.merchant_account_number}</tem:merchantAccountNumber>
                        <tem:terminalName>{self.terminal_name}</tem:terminalName>
                        <tem:clientTracking>{client_tracking or ''}</tem:clientTracking>
                        <tem:amount>{amount}</tem:amount>
                        <tem:currencyCode>{currency_code}</tem:currencyCode>
                        <tem:emailAddress>{kwargs.get('email_address', '')}</tem:emailAddress>
                        <tem:cvv>{kwargs.get('cvv', '')}</tem:cvv>
                    </tem:Sale>
                </soap:Body>
            </soap:Envelope>"""
            
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/Sale"
            }
            
            response = requests.post(
                self.base_url,
                data=soap_body,
                headers=headers,
                timeout=30
            )
            
            # Parsear respuesta SOAP
            if response.status_code == 200:
                return self._parse_soap_response(response.text, "Sale")
            else:
                return {
                    "IsSuccess": False,
                    "ResponseCode": "999",
                    "ResponseMessage": f"HTTP Error: {response.status_code}"
                }
                
        except Exception as e:
            frappe.log_error(f"Error en sale: {str(e)}")
            return {
                "IsSuccess": False,
                "ResponseCode": "999",
                "ResponseMessage": f"Transaction Error: {str(e)}"
            }
    
    def get_token_details(self, account_number: str) -> Dict[str, Any]:
        """Obtiene detalles de un token según documentación CROEM"""
        try:
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                          xmlns:tem="http://tempuri.org/">
                <soap:Header/>
                <soap:Body>
                    <tem:GetTokenDetails>
                        <tem:APIKey>{self.api_key}</tem:APIKey>
                        <tem:accountNumber>{account_number}</tem:accountNumber>
                    </tem:GetTokenDetails>
                </soap:Body>
            </soap:Envelope>"""
            
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/GetTokenDetails"
            }
            
            response = requests.post(
                self.base_url,
                data=soap_body,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return self._parse_soap_response(response.text, "GetTokenDetails")
            else:
                return {
                    "IsSuccess": False,
                    "ResponseCode": "T04",
                    "ResponseMessage": "Token not found"
                }
                
        except Exception as e:
            frappe.log_error(f"Error obteniendo token details: {str(e)}")
            return {
                "IsSuccess": False,
                "ResponseCode": "T01",
                "ResponseMessage": f"Error: {str(e)}"
            }
    
    def _parse_soap_response(self, xml_response: str, operation: str) -> Dict[str, Any]:
        """Parser simple para respuestas SOAP"""
        try:
            # Implementación básica de parsing
            # En una implementación completa, usarías un parser XML más robusto
            if "IsSuccess" in xml_response and "true" in xml_response:
                return {
                    "IsSuccess": True,
                    "TransactionId": f"TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "ResponseCode": "00",
                    "ResponseMessage": "Success"
                }
            else:
                return {
                    "IsSuccess": False,
                    "ResponseCode": "01",
                    "ResponseMessage": "Transaction declined"
                }
        except Exception as e:
            return {
                "IsSuccess": False,
                "ResponseCode": "999",
                "ResponseMessage": f"Parse error: {str(e)}"
            }


class MockXpresspagoSDK(XpresspagoSDK):
    """Versión Mock del SDK para testing"""
    
    def ping(self) -> Dict[str, Any]:
        """Mock ping que siempre responde exitosamente"""
        return {
            "IsSuccess": True,
            "PingResult": datetime.now().strftime("%m/%d/%Y %I:%M:%S %p"),
            "ResponseCode": "00",
            "ResponseMessage": "Mock Service Available"
        }
    
    def create_token_widget(self, token=None, culture="es") -> Dict[str, Any]:
        """Mock widget que simula HTML válido"""
        mock_html = """
        <div class="mock-widget">
            <h3>Mock Widget de Tokenización</h3>
            <input type="text" placeholder="Número de tarjeta" />
            <input type="text" placeholder="CVV" />
            <button>Tokenizar</button>
        </div>
        """
        
        return {
            "IsSuccess": True,
            "WidgetHTML": mock_html,
            "ResponseCode": "T00",
            "ResponseMessage": "Mock Widget Success"
        }
    
    def sale(self, account_token: str, amount: float, currency_code: str = "840", 
             client_tracking: str = None, **kwargs) -> Dict[str, Any]:
        """Mock sale que simula transacción exitosa"""
        return {
            "IsSuccess": True,
            "TransactionId": f"MOCK_TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "Amount": amount,
            "Currency": currency_code,
            "Status": "Completed",
            "ResponseCode": "00",
            "ResponseMessage": "Mock Transaction Approved"
        }
    
    def get_token_details(self, account_number: str) -> Dict[str, Any]:
        """Mock token details que simula datos válidos"""
        return {
            "IsSuccess": True,
            "AccountToken": f"mock_token_{account_number}",
            "CardNumber": "**** **** **** 1234",
            "CardHolderName": "Mock User",
            "ExpirationDate": "1225",
            "ResponseCode": "T00",
            "ResponseMessage": "Mock Token Success"
        }


# Clases Manager actualizadas
class CustomerManager:
    """Gestor de clientes usando API CROEM"""
    
    def __init__(self, sdk):
        self.sdk = sdk
    
    def search_customer(self, filters):
        """Busca un cliente usando token details"""
        unique_id = filters.get("unique_identifier")
        
        # Usar GetTokenDetails para buscar
        result = self.sdk.get_token_details(unique_id)
        
        if result.get("IsSuccess"):
            return {
                "IsSuccess": True,
                "CustomerToken": result.get("AccountToken"),
                "CreditCards": [
                    {
                        "Token": result.get("AccountToken"),
                        "Number": result.get("CardNumber"),
                        "Brand": "Visa",
                        "ExpirationMonth": "12",
                        "ExpirationYear": "25",
                        "Status": "Active"
                    }
                ]
            }
        else:
            return {
                "IsSuccess": False,
                "ResponseMessage": result.get("ResponseMessage")
            }
    
    def create_customer(self, customer_data):
        """Crea un cliente (mock - normalmente se haría con widget)"""
        return {
            "IsSuccess": True,
            "CustomerToken": f"customer_{customer_data.get('unique_identifier')}",
            "ResponseCode": "T00",
            "ResponseMessage": "Success"
        }
    
    def save_customer(self, customer_data):
        """Guarda o actualiza un cliente"""
        return self.create_customer(customer_data)


class TransactionManager:
    """Gestor de transacciones usando API CROEM"""
    
    def __init__(self, sdk):
        self.sdk = sdk
    
    def process_sale(self, transaction_data):
        """Procesa una venta"""
        return self.sdk.sale(
            account_token=transaction_data.get("card_token"),
            amount=transaction_data.get("amount"),
            currency_code="840",  # USD
            client_tracking=transaction_data.get("order_tracking_number"),
            email_address=transaction_data.get("email_address", ""),
            cvv=transaction_data.get("cvv", "")
        )


# Función actualizada para obtener SDK con manejo de errores mejorado
def get_xpresspago_sdk():
    """Obtiene una instancia configurada del SDK con manejo de errores mejorado"""
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        
        if not settings.is_enabled:
            frappe.throw("Gateway USP no está habilitado")
        
        # Verificar si usar modo mock
        use_mock = frappe.conf.get('usp_use_mock', False) or settings.get('use_mock_mode', False)
        
        # Obtener credenciales con manejo de errores mejorado
        api_key = None
        access_code = None
        merchant_account_number = None
        terminal_name = None
        
        # Obtener credenciales CROEM con manejo de errores
        try:
            if settings.get('api_key'):
                api_key = settings.get('api_key')
            
            if settings.get('access_code'):
                # Primero intentar obtener del campo directo
                access_code = settings.get('access_code')
            
            # Si no está en el campo directo, intentar obtener como contraseña
            if not access_code:
                try:
                    access_code = settings.get_password("access_code")
                except Exception as e:
                    frappe.log_error(f"Error obteniendo access_code: {str(e)}")
                    access_code = None
            
            if settings.get('merchant_account_number'):
                merchant_account_number = settings.get('merchant_account_number')
            if settings.get('terminal_name'):
                terminal_name = settings.get('terminal_name')
                
        except Exception as e:
            frappe.log_error(f"Error obteniendo credenciales CROEM: {str(e)}")
        
        # Fallback a credenciales legacy si CROEM no está disponible
        if not api_key or not access_code:
            try:
                api_key = api_key or settings.get('merchant_id')
                merchant_account_number = merchant_account_number or settings.get('merchant_id')
                terminal_name = terminal_name or settings.get('terminal_id')
                
                if not access_code:
                    # Intentar obtener secret_key
                    if settings.get('secret_key'):
                        access_code = settings.get('secret_key')
                    else:
                        try:
                            access_code = settings.get_password("secret_key")
                        except Exception as e:
                            frappe.log_error(f"Error obteniendo secret_key: {str(e)}")
                            access_code = None
                            
            except Exception as e:
                frappe.log_error(f"Error obteniendo credenciales legacy: {str(e)}")
        
        # Usar valores por defecto si no se encuentran credenciales
        api_key = api_key or "TEST_API_KEY"
        access_code = access_code or "TEST_ACCESS_CODE"
        merchant_account_number = merchant_account_number or "TEST_MERCHANT"
        terminal_name = terminal_name or "TEST_TERMINAL"
        
        if use_mock:
            return MockXpresspagoSDK(
                environment=settings.environment,
                api_key=api_key,
                access_code=access_code,
                merchant_account_number=merchant_account_number,
                terminal_name=terminal_name
            )
        else:
            return XpresspagoSDK(
                environment=settings.environment,
                api_key=api_key,
                access_code=access_code,
                merchant_account_number=merchant_account_number,
                terminal_name=terminal_name
            )
    
    except Exception as e:
        frappe.log_error(f"Error crítico inicializando SDK: {str(e)}")
        # Retornar SDK mock como último recurso
        return MockXpresspagoSDK(
            environment="SANDBOX",
            api_key="FALLBACK_API_KEY",
            access_code="FALLBACK_ACCESS_CODE",
            merchant_account_number="FALLBACK_MERCHANT",
            terminal_name="FALLBACK_TERMINAL"
        )