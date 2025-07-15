# Copyright (c) 2024, EduTech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url

class USPPaymentGatewaySettings(Document):
    def validate(self):
        """Validaciones antes de guardar"""
        if self.is_enabled:
            self.validate_required_fields()
            self.generate_webhook_url()
            self.handle_compatibility()
    
    def validate_required_fields(self):
        """Validar campos requeridos cuando está habilitado"""
        # Verificar si se están usando credenciales CROEM o legacy
        if self.has_croem_credentials():
            required_fields = ['api_key', 'merchant_account_number', 'terminal_name']
            missing_fields = []
            
            for field in required_fields:
                if not self.get(field):
                    missing_fields.append(field)
            
            # Validar access_code por separado (campo Password)
            if not self.get('access_code'):
                try:
                    access_code = self.get_password('access_code')
                    if not access_code:
                        missing_fields.append('access_code')
                except:
                    missing_fields.append('access_code')
            
            if missing_fields:
                frappe.throw(f"Los siguientes campos CROEM son requeridos: {', '.join(missing_fields)}")
        
        elif self.has_legacy_credentials():
            required_fields = ['merchant_id']
            missing_fields = []
            
            for field in required_fields:
                if not self.get(field):
                    missing_fields.append(field)
            
            # Validar secret_key por separado (campo Password)
            if not self.get('secret_key'):
                try:
                    secret_key = self.get_password('secret_key')
                    if not secret_key:
                        missing_fields.append('secret_key')
                except:
                    missing_fields.append('secret_key')
            
            if missing_fields:
                frappe.throw(f"Los siguientes campos legacy son requeridos: {', '.join(missing_fields)}")
        
        else:
            frappe.throw("Debe configurar credenciales CROEM (recomendado) o credenciales legacy")
    
    def has_croem_credentials(self):
        """Verificar si tiene credenciales CROEM configuradas"""
        has_api_key = bool(self.get('api_key'))
        has_access_code = False
        
        try:
            access_code = self.get_password('access_code')
            has_access_code = bool(access_code)
        except:
            has_access_code = False
        
        return has_api_key and has_access_code
    
    def has_legacy_credentials(self):
        """Verificar si tiene credenciales legacy configuradas"""
        has_merchant_id = bool(self.get('merchant_id'))
        has_secret_key = False
        
        try:
            secret_key = self.get_password('secret_key')
            has_secret_key = bool(secret_key)
        except:
            has_secret_key = False
        
        return has_merchant_id and has_secret_key
    
    def handle_compatibility(self):
        """Manejar compatibilidad entre campos CROEM y legacy"""
        # Si se configuraron credenciales CROEM, mapear a campos legacy para compatibilidad
        if self.has_croem_credentials():
            if not self.merchant_id:
                self.merchant_id = self.merchant_account_number
            if not self.terminal_id:
                self.terminal_id = self.terminal_name
        
        # Si solo hay credenciales legacy, sugerir migración
        elif self.has_legacy_credentials() and not self.has_croem_credentials():
            frappe.msgprint(
                "Está usando credenciales legacy. Se recomienda migrar a credenciales CROEM API Token v6.5 para mejor funcionalidad.",
                indicator="yellow",
                title="Migración Recomendada"
            )
    
    def generate_webhook_url(self):
        """Generar URL del webhook automáticamente"""
        if not self.webhook_url:
            site_url = get_url()
            self.webhook_url = f"{site_url}/api/method/gateway_usp.api.payment_controller.webhook_handler"
    
    def on_update(self):
        """Después de actualizar"""
        if self.is_enabled and not self.use_mock_mode:
            self.test_connection()
    
    def test_connection(self):
        """Probar conexión con XpressPago usando SDK actualizado"""
        try:
            from gateway_usp.api.xpresspago_sdk import get_xpresspago_sdk
            
            # Obtener SDK configurado automáticamente
            sdk = get_xpresspago_sdk()
            
            # Probar ping según documentación CROEM
            ping_result = sdk.ping()
            
            if ping_result.get("IsSuccess"):
                frappe.msgprint(
                    f"Conexión exitosa con USP Gateway<br>"
                    f"Ping Result: {ping_result.get('PingResult')}<br>"
                    f"Response Code: {ping_result.get('ResponseCode')}<br>"
                    f"Environment: {self.environment}",
                    indicator="green",
                    title="Conexión Exitosa"
                )
            else:
                frappe.msgprint(
                    f"Error en conexión USP Gateway<br>"
                    f"Error: {ping_result.get('ResponseMessage')}<br>"
                    f"Response Code: {ping_result.get('ResponseCode')}",
                    indicator="orange",
                    title="Error de Conexión"
                )
            
        except Exception as e:
            frappe.log_error(f"Error probando conexión USP: {str(e)}")
            frappe.msgprint(f"Error de conexión: {str(e)}", indicator="red")

    @frappe.whitelist()
    def sync_settings(self):
        """Sincronizar configuraciones con XpressPago"""
        self.last_sync = frappe.utils.now()
        self.save()
        frappe.msgprint("Configuraciones sincronizadas", indicator="green")
    
    @frappe.whitelist()
    def test_connectivity_page(self):
        """Abrir página de pruebas de conectividad"""
        return "/test_connectivity"
    
    @frappe.whitelist()
    def run_diagnostics(self):
        """Ejecutar diagnósticos completos"""
        try:
            from gateway_usp.utils.network_test import run_full_connectivity_test
            
            results = run_full_connectivity_test()
            
            if results.get("overall_success"):
                frappe.msgprint(
                    "Todos los diagnósticos pasaron exitosamente",
                    indicator="green",
                    title="Diagnósticos Completos"
                )
            else:
                failed_tests = []
                for test_name, test_result in results.get("tests", {}).items():
                    if not test_result.get("success"):
                        failed_tests.append(test_name)
                
                frappe.msgprint(
                    f"Algunos diagnósticos fallaron: {', '.join(failed_tests)}<br>"
                    f"Consulte la página de pruebas de conectividad para detalles.",
                    indicator="orange",
                    title="Diagnósticos con Errores"
                )
            
            return results
            
        except Exception as e:
            frappe.log_error(f"Error ejecutando diagnósticos USP: {str(e)}")
            frappe.msgprint(f"Error en diagnósticos: {str(e)}", indicator="red")
            return {"overall_success": False, "error": str(e)}
    
    @frappe.whitelist()
    def migrate_to_croem(self):
        """Migrar configuración legacy a CROEM"""
        if self.has_legacy_credentials() and not self.has_croem_credentials():
            # Mapear campos legacy a CROEM
            self.api_key = self.merchant_id
            self.merchant_account_number = self.merchant_id
            self.terminal_name = self.terminal_id or f"TERM_{self.merchant_id}"
            
            # Copiar contraseñas
            try:
                secret_key = self.get_password('secret_key')
                if secret_key:
                    self.access_code = secret_key
            except:
                pass
            
            # Guardar cambios
            self.save()
            
            frappe.msgprint(
                "Migración a credenciales CROEM completada exitosamente",
                indicator="green",
                title="Migración Completa"
            )
            
            return True
        else:
            frappe.msgprint(
                "No se requiere migración o ya tiene credenciales CROEM configuradas",
                indicator="blue",
                title="Migración No Requerida"
            )
            return False
    
    @frappe.whitelist()
    def reset_password_fields(self):
        """Resetear campos de contraseña si hay problemas"""
        try:
            if self.access_code:
                self.set_password('access_code', self.access_code)
            if self.secret_key:
                self.set_password('secret_key', self.secret_key)
            
            self.save()
            frappe.msgprint("Campos de contraseña reseteados exitosamente", indicator="green")
            
        except Exception as e:
            frappe.log_error(f"Error reseteando contraseñas: {str(e)}")
            frappe.msgprint(f"Error reseteando contraseñas: {str(e)}", indicator="red")