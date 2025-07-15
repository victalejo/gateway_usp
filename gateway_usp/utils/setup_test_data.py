import frappe

def setup_test_credentials():
    """Configura credenciales de prueba para desarrollo"""
    
    try:
        # Obtener o crear documento de configuración
        if frappe.db.exists("USP Payment Gateway Settings"):
            settings = frappe.get_single("USP Payment Gateway Settings")
        else:
            settings = frappe.new_doc("USP Payment Gateway Settings")
        
        # Configurar valores de prueba
        settings.is_enabled = 1
        settings.environment = "SANDBOX"
        settings.use_mock_mode = 1
        
        # Credenciales CROEM de prueba
        settings.api_key = "TEST_API_KEY_DEVELOPMENT"
        settings.merchant_account_number = "TEST_MERCHANT_123"
        settings.terminal_name = "TEST_TERMINAL_456"
        
        # Credenciales legacy de respaldo
        settings.merchant_id = "TEST_MERCHANT_123"
        settings.terminal_id = "TEST_TERMINAL_456"
        
        # Configuración adicional
        settings.default_currency = "USD"
        settings.payment_timeout = 300
        settings.auto_capture = 1
        
        # Guardar configuración
        settings.save()
        
        # Establecer contraseñas por separado
        try:
            settings.set_password("access_code", "TEST_ACCESS_CODE_DEVELOPMENT")
            settings.set_password("secret_key", "TEST_SECRET_KEY_DEVELOPMENT")
        except Exception as e:
            frappe.log_error(f"Error estableciendo contraseñas: {str(e)}")
        
        frappe.db.commit()
        
        frappe.msgprint("Credenciales de prueba configuradas exitosamente", indicator="green")
        
    except Exception as e:
        frappe.log_error(f"Error configurando credenciales de prueba: {str(e)}")
        frappe.msgprint(f"Error: {str(e)}", indicator="red")

if __name__ == "__main__":
    setup_test_credentials() 