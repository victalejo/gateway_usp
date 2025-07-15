# gateway_usp/utils/network_test.py

import frappe
from gateway_usp.api.xpresspago_sdk import get_xpresspago_sdk

@frappe.whitelist()
def verify_password_fields():
    """Verificar acceso a campos de contraseña en USP Settings"""
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        
        results = {
            "success": True,
            "access_code_status": "not_configured",
            "secret_key_status": "not_configured",
            "errors": []
        }
        
        # Verificar access_code
        if settings.get('access_code'):
            try:
                access_code = settings.get_password('access_code')
                if access_code:
                    results["access_code_status"] = "ok"
                else:
                    results["access_code_status"] = "field_only"
                    results["errors"].append("access_code: campo visible pero contraseña vacía")
            except Exception as e:
                results["access_code_status"] = "error"
                results["errors"].append(f"access_code: error accediendo ({str(e)})")
        
        # Verificar secret_key  
        if settings.get('secret_key'):
            try:
                secret_key = settings.get_password('secret_key')
                if secret_key:
                    results["secret_key_status"] = "ok"
                else:
                    results["secret_key_status"] = "field_only"
                    results["errors"].append("secret_key: campo visible pero contraseña vacía")
            except Exception as e:
                results["secret_key_status"] = "error"
                results["errors"].append(f"secret_key: error accediendo ({str(e)})")
        
        if results["errors"]:
            results["success"] = False
            results["message"] = f"Problemas detectados en campos de contraseña: {'; '.join(results['errors'])}"
        else:
            results["message"] = "Campos de contraseña configurados correctamente"
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error verificando campos de contraseña: {str(e)}")
        return {
            "success": False,
            "message": "Error verificando campos de contraseña",
            "error": str(e)
        }

@frappe.whitelist()
def test_usp_connectivity():
    """Prueba conectividad usando método Ping de la documentación CROEM"""
    try:
        sdk = get_xpresspago_sdk()
        
        # Usar método ping de la documentación
        ping_result = sdk.ping()
        
        if ping_result.get("IsSuccess"):
            return {
                "success": True,
                "message": "Conectividad exitosa con USP Gateway",
                "ping_result": ping_result.get("PingResult"),
                "response_code": ping_result.get("ResponseCode"),
                "environment": sdk.environment,
                "api_key": f"***{sdk.api_key[-4:]}" if sdk.api_key else "No configurado"
            }
        else:
            return {
                "success": False,
                "message": "Fallo en conectividad con USP Gateway",
                "error": ping_result.get("ResponseMessage"),
                "response_code": ping_result.get("ResponseCode"),
                "environment": sdk.environment
            }
    
    except Exception as e:
        frappe.log_error(f"Error en test de conectividad USP: {str(e)}")
        return {
            "success": False,
            "message": "Error en prueba de conectividad",
            "error": str(e)
        }

@frappe.whitelist()
def test_widget_loading():
    """Prueba carga del widget de tokenización según documentación CROEM"""
    try:
        sdk = get_xpresspago_sdk()
        
        # Probar widget en español
        widget_result = sdk.create_token_widget(culture="es")
        
        if widget_result.get("IsSuccess"):
            return {
                "success": True,
                "message": "Widget cargado exitosamente",
                "has_html": bool(widget_result.get("WidgetHTML")),
                "response_code": widget_result.get("ResponseCode"),
                "html_length": len(widget_result.get("WidgetHTML", ""))
            }
        else:
            return {
                "success": False,
                "message": "Error cargando widget",
                "error": widget_result.get("ResponseMessage"),
                "response_code": widget_result.get("ResponseCode")
            }
    
    except Exception as e:
        frappe.log_error(f"Error probando widget USP: {str(e)}")
        return {
            "success": False,
            "message": "Error probando widget",
            "error": str(e)
        }

@frappe.whitelist()
def test_mock_transaction():
    """Prueba transacción mock usando el SDK CROEM"""
    try:
        sdk = get_xpresspago_sdk()
        
        # Simular datos de transacción de prueba
        test_transaction = {
            "card_token": "test_token_12345",
            "amount": 10.00,
            "order_tracking_number": f"TEST_{frappe.utils.now()}",
            "email_address": "test@example.com",
            "cvv": "123"
        }
        
        # Procesar venta de prueba
        sale_result = sdk.sale(
            account_token=test_transaction["card_token"],
            amount=test_transaction["amount"],
            currency_code="840",  # USD
            client_tracking=test_transaction["order_tracking_number"],
            email_address=test_transaction["email_address"],
            cvv=test_transaction["cvv"]
        )
        
        if sale_result.get("IsSuccess"):
            return {
                "success": True,
                "message": "Transacción de prueba exitosa",
                "transaction_id": sale_result.get("TransactionId"),
                "amount": sale_result.get("Amount"),
                "response_code": sale_result.get("ResponseCode"),
                "status": sale_result.get("Status", "Completed")
            }
        else:
            return {
                "success": False,
                "message": "Error en transacción de prueba",
                "error": sale_result.get("ResponseMessage"),
                "response_code": sale_result.get("ResponseCode")
            }
    
    except Exception as e:
        frappe.log_error(f"Error en transacción de prueba USP: {str(e)}")
        return {
            "success": False,
            "message": "Error procesando transacción de prueba",
            "error": str(e)
        }

@frappe.whitelist()
def test_token_details():
    """Prueba obtención de detalles de token según documentación CROEM"""
    try:
        sdk = get_xpresspago_sdk()
        
        # Probar con un número de cuenta de prueba
        test_account_number = "test_account_12345"
        
        token_result = sdk.get_token_details(test_account_number)
        
        if token_result.get("IsSuccess"):
            return {
                "success": True,
                "message": "Detalles de token obtenidos exitosamente",
                "account_token": token_result.get("AccountToken"),
                "card_number": token_result.get("CardNumber"),
                "cardholder_name": token_result.get("CardHolderName"),
                "expiration_date": token_result.get("ExpirationDate"),
                "response_code": token_result.get("ResponseCode")
            }
        else:
            return {
                "success": False,
                "message": "Error obteniendo detalles de token",
                "error": token_result.get("ResponseMessage"),
                "response_code": token_result.get("ResponseCode")
            }
    
    except Exception as e:
        frappe.log_error(f"Error obteniendo token details USP: {str(e)}")
        return {
            "success": False,
            "message": "Error obteniendo detalles de token",
            "error": str(e)
        }

@frappe.whitelist()
def get_usp_configuration():
    """Obtiene y valida la configuración actual de USP Gateway"""
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        
        # Verificar campos de contraseña
        password_check = verify_password_fields()
        
        config_info = {
            "is_enabled": settings.is_enabled,
            "environment": settings.environment,
            "use_mock": frappe.conf.get('usp_use_mock', False),
            "password_fields_status": password_check,
            # Credenciales CROEM
            "api_key": f"***{settings.api_key[-4:]}" if settings.api_key else "No configurado",
            "merchant_account_number": settings.merchant_account_number or "No configurado",
            "terminal_name": settings.terminal_name or "No configurado",
            "has_access_code": password_check.get("access_code_status") == "ok",
            # Credenciales Legacy
            "merchant_id": f"***{settings.merchant_id[-4:]}" if settings.merchant_id else "No configurado",
            "terminal_id": settings.terminal_id or "No configurado", 
            "has_secret_key": password_check.get("secret_key_status") == "ok"
        }
        
        # Validar configuración
        errors = []
        if not settings.is_enabled:
            errors.append("Gateway USP no está habilitado")
        
        # Verificar si tiene credenciales CROEM válidas
        has_croem = (settings.api_key and 
                     settings.merchant_account_number and 
                     settings.terminal_name and 
                     password_check.get("access_code_status") == "ok")
        
        # Verificar si tiene credenciales legacy válidas
        has_legacy = (settings.merchant_id and 
                      settings.terminal_id and 
                      password_check.get("secret_key_status") == "ok")
        
        if not has_croem and not has_legacy:
            errors.append("No hay credenciales válidas configuradas (ni CROEM ni legacy)")
        
        # Agregar errores de campos de contraseña
        if not password_check.get("success"):
            errors.extend(password_check.get("errors", []))
        
        return {
            "success": len(errors) == 0,
            "message": "Configuración válida" if len(errors) == 0 else "Errores en configuración",
            "configuration": config_info,
            "errors": errors,
            "has_croem_credentials": has_croem,
            "has_legacy_credentials": has_legacy
        }
    
    except Exception as e:
        frappe.log_error(f"Error obteniendo configuración USP: {str(e)}")
        return {
            "success": False,
            "message": "Error obteniendo configuración",
            "error": str(e)
        }

@frappe.whitelist()
def run_full_connectivity_test():
    """Ejecuta todas las pruebas de conectividad en secuencia"""
    try:
        results = {
            "timestamp": frappe.utils.now(),
            "overall_success": True,
            "tests": {}
        }
        
        # Test 1: Configuración
        config_test = get_usp_configuration()
        results["tests"]["configuration"] = config_test
        if not config_test.get("success"):
            results["overall_success"] = False
        
        # Test 2: Ping/Conectividad
        ping_test = test_usp_connectivity()
        results["tests"]["connectivity"] = ping_test
        if not ping_test.get("success"):
            results["overall_success"] = False
        
        # Test 3: Widget
        widget_test = test_widget_loading()
        results["tests"]["widget"] = widget_test
        if not widget_test.get("success"):
            results["overall_success"] = False
        
        # Test 4: Token Details
        token_test = test_token_details()
        results["tests"]["token_details"] = token_test
        if not token_test.get("success"):
            results["overall_success"] = False
        
        # Test 5: Transacción Mock
        transaction_test = test_mock_transaction()
        results["tests"]["transaction"] = transaction_test
        if not transaction_test.get("success"):
            results["overall_success"] = False
        
        return results
    
    except Exception as e:
        frappe.log_error(f"Error en prueba completa de conectividad USP: {str(e)}")
        return {
            "overall_success": False,
            "error": str(e),
            "timestamp": frappe.utils.now()
        } 