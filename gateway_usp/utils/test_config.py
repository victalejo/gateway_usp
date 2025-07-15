# gateway_usp/utils/test_config.py

import frappe
import os

def setup_test_environment():
    """Configura el ambiente de pruebas para USP Gateway"""
    
    # Configurar modo mock en frappe.conf
    frappe.conf.usp_use_mock = True
    
    # Crear configuración de prueba si no existe
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
    except:
        # Crear documento de configuración
        settings = frappe.new_doc("USP Payment Gateway Settings")
    
    # Configurar valores de prueba
    test_config = {
        "is_enabled": 1,
        "environment": "SANDBOX",
        "use_mock_mode": 1,
        
        # Credenciales CROEM de prueba
        "api_key": "TEST_API_KEY_12345",
        "access_code": "TEST_ACCESS_CODE_67890",
        "merchant_account_number": "TEST_MERCHANT_123",
        "terminal_name": "TEST_TERMINAL_456",
        
        # Credenciales legacy de respaldo
        "merchant_id": "TEST_MERCHANT_123",
        "secret_key": "TEST_SECRET_KEY_LEGACY",
        "terminal_id": "TEST_TERMINAL_456",
        
        # Configuración de pagos
        "default_currency": "USD",
        "payment_timeout": 300,
        "auto_capture": 1,
        "send_notifications": 0,
        
        # URLs de prueba
        "success_url": "http://localhost:8000/success",
        "failure_url": "http://localhost:8000/failure",
        "cancel_url": "http://localhost:8000/cancel"
    }
    
    # Aplicar configuración
    for field, value in test_config.items():
        settings.set(field, value)
    
    # Guardar configuración
    settings.save()
    frappe.db.commit()
    
    print("✅ Configuración de prueba USP Gateway establecida")
    return settings

def reset_test_environment():
    """Reinicia el ambiente de pruebas"""
    
    # Deshabilitar modo mock
    frappe.conf.usp_use_mock = False
    
    # Limpiar configuración de prueba
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        settings.is_enabled = 0
        settings.use_mock_mode = 0
        settings.save()
        frappe.db.commit()
        print("✅ Ambiente de prueba reiniciado")
    except:
        print("⚠️ No se pudo reiniciar el ambiente de prueba")

@frappe.whitelist()
def run_integration_tests():
    """Ejecuta pruebas de integración completas"""
    
    print("🧪 Iniciando pruebas de integración USP Gateway...")
    
    # Configurar ambiente de prueba
    setup_test_environment()
    
    results = {
        "timestamp": frappe.utils.now(),
        "tests": {},
        "overall_success": True
    }
    
    try:
        # Test 1: Configuración
        print("📋 Test 1: Configuración...")
        from gateway_usp.utils.network_test import get_usp_configuration
        config_result = get_usp_configuration()
        results["tests"]["configuration"] = config_result
        print(f"   {'✅' if config_result.get('success') else '❌'} Configuración")
        
        # Test 2: SDK Initialization
        print("🔧 Test 2: Inicialización SDK...")
        try:
            from gateway_usp.api.xpresspago_sdk import get_xpresspago_sdk
            sdk = get_xpresspago_sdk()
            sdk_result = {"success": True, "message": "SDK inicializado correctamente"}
            print("   ✅ SDK inicializado")
        except Exception as e:
            sdk_result = {"success": False, "message": f"Error: {str(e)}"}
            print(f"   ❌ Error SDK: {str(e)}")
        
        results["tests"]["sdk_init"] = sdk_result
        
        # Test 3: Ping
        print("📡 Test 3: Conectividad...")
        from gateway_usp.utils.network_test import test_usp_connectivity
        ping_result = test_usp_connectivity()
        results["tests"]["ping"] = ping_result
        print(f"   {'✅' if ping_result.get('success') else '❌'} Ping")
        
        # Test 4: Widget
        print("🖼️ Test 4: Widget...")
        from gateway_usp.utils.network_test import test_widget_loading
        widget_result = test_widget_loading()
        results["tests"]["widget"] = widget_result
        print(f"   {'✅' if widget_result.get('success') else '❌'} Widget")
        
        # Test 5: Token Details
        print("🔑 Test 5: Token Details...")
        from gateway_usp.utils.network_test import test_token_details
        token_result = test_token_details()
        results["tests"]["token"] = token_result
        print(f"   {'✅' if token_result.get('success') else '❌'} Token Details")
        
        # Test 6: Transacción Mock
        print("💳 Test 6: Transacción...")
        from gateway_usp.utils.network_test import test_mock_transaction
        transaction_result = test_mock_transaction()
        results["tests"]["transaction"] = transaction_result
        print(f"   {'✅' if transaction_result.get('success') else '❌'} Transacción")
        
        # Test 7: Payment Controller
        print("💰 Test 7: Payment Controller...")
        try:
            from gateway_usp.api.payment_controller import process_payment_with_new_card
            
            test_payment_data = {
                "amount": 10.00,
                "currency": "USD",
                "customer": "Test Customer",
                "reference_doctype": "Test Document",
                "reference_docname": "TEST-001",
                "card_data": {
                    "card_number": "4111111111111111",
                    "cardholder_name": "Test User",
                    "expiry_month": "12",
                    "expiry_year": "2025",
                    "cvv": "123",
                    "save_card": False
                }
            }
            
            payment_result = process_payment_with_new_card(test_payment_data)
            print(f"   {'✅' if payment_result.get('success') else '❌'} Payment Controller")
            
        except Exception as e:
            payment_result = {"success": False, "message": f"Error: {str(e)}"}
            print(f"   ❌ Payment Controller: {str(e)}")
        
        results["tests"]["payment_controller"] = payment_result
        
        # Calcular resultado general
        failed_tests = []
        for test_name, test_result in results["tests"].items():
            if not test_result.get("success"):
                failed_tests.append(test_name)
                results["overall_success"] = False
        
        if results["overall_success"]:
            print("\n🎉 ¡Todas las pruebas de integración pasaron exitosamente!")
        else:
            print(f"\n⚠️ Algunas pruebas fallaron: {', '.join(failed_tests)}")
        
    except Exception as e:
        print(f"\n❌ Error en pruebas de integración: {str(e)}")
        results["overall_success"] = False
        results["error"] = str(e)
    
    finally:
        # Limpiar ambiente de prueba
        print("\n🧹 Limpiando ambiente de prueba...")
        reset_test_environment()
    
    return results

if __name__ == "__main__":
    # Ejecutar pruebas cuando se llama directamente
    run_integration_tests() 