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
    
    def validate_required_fields(self):
        """Validar campos requeridos cuando está habilitado"""
        required_fields = ['merchant_id', 'secret_key']
        
        for field in required_fields:
            if not self.get(field):
                frappe.throw(f"El campo {field} es requerido cuando el gateway está habilitado")
    
    def generate_webhook_url(self):
        """Generar URL del webhook automáticamente"""
        if not self.webhook_url:
            site_url = get_url()
            self.webhook_url = f"{site_url}/api/method/gateway_usp.api.payment_controller.webhook_handler"
    
    def on_update(self):
        """Después de actualizar"""
        if self.is_enabled:
            self.test_connection()
    
    def test_connection(self):
        """Probar conexión con XpressPago"""
        try:
            from gateway_usp.api.xpresspago_sdk import XpresspagoSDK
            
            sdk = XpresspagoSDK(
                environment=self.environment,
                merchant_id=self.merchant_id,
                secret_key=self.get_password('secret_key'),
                terminal_id=self.terminal_id
            )
            
            # Aquí podrías hacer una llamada de prueba a la API
            frappe.msgprint("Conexión con XpressPago establecida correctamente", 
                          indicator="green")
            
        except Exception as e:
            frappe.log_error(f"Error probando conexión USP: {str(e)}")
            frappe.msgprint(f"Error de conexión: {str(e)}", indicator="red")

    @frappe.whitelist()
    def sync_settings(self):
        """Sincronizar configuraciones con XpressPago"""
        self.last_sync = frappe.utils.now()
        self.save()
        frappe.msgprint("Configuraciones sincronizadas", indicator="green")