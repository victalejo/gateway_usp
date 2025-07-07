# Copyright (c) 2024, EduTech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, flt
import json

class USPTransaction(Document):
    def before_insert(self):
        """Antes de insertar"""
        if not self.created_at:
            self.created_at = now()
        
        # Generar transaction_id si no existe
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
    
    def validate(self):
        """Validaciones antes de guardar"""
        # Validar monto
        if flt(self.amount) <= 0:
            frappe.throw("El monto debe ser mayor a cero")
        
        # Validar estado
        if self.status not in ["Pending", "Authorized", "Completed", "Failed", "Cancelled", "Refunded", "Partially Refunded"]:
            frappe.throw("Estado de transacción inválido")
    
    def before_save(self):
        """Antes de guardar"""
        self.updated_at = now()
        
        # Actualizar fechas según estado
        if self.status == "Completed" and not self.completed_at:
            self.completed_at = now()
        elif self.status in ["Authorized", "Failed", "Cancelled"] and not self.processed_at:
            self.processed_at = now()
    
    def generate_transaction_id(self):
        """Generar ID de transacción único"""
        import random
        import string
        
        timestamp = str(int(frappe.utils.now_datetime().timestamp()))
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        return f"USP-{timestamp}-{random_chars}"
    
    @frappe.whitelist()
    def retry_payment(self):
        """Reintentar pago"""
        if self.status not in ["Failed", "Cancelled"]:
            frappe.throw("Solo se pueden reintentar pagos fallidos o cancelados")
        
        # Resetear estado
        self.status = "Pending"
        self.error_message = None
        self.processed_at = None
        self.completed_at = None
        self.save()
        
        frappe.msgprint("Pago marcado para reintento", indicator="blue")
    
    @frappe.whitelist()
    def cancel_transaction(self):
        """Cancelar transacción"""
        if self.status == "Completed":
            frappe.throw("No se puede cancelar una transacción completada")
        
        self.status = "Cancelled"
        self.processed_at = now()
        self.save()
        
        frappe.msgprint("Transacción cancelada", indicator="orange")
    
    def on_update(self):
        """Después de actualizar"""
        # Notificar cambios de estado importantes
        if self.status == "Completed":
            self.send_completion_notification()
        elif self.status == "Failed":
            self.send_failure_notification()
    
    def send_completion_notification(self):
        """Enviar notificación de pago completado"""
        if self.customer:
            customer_doc = frappe.get_doc("Customer", self.customer)
            if customer_doc.email_id:
                frappe.sendmail(
                    recipients=[customer_doc.email_id],
                    subject="Pago Completado - USP Gateway",
                    message=f"""
                    <h3>Pago Completado</h3>
                    <p>Su pago ha sido procesado exitosamente:</p>
                    <ul>
                        <li><strong>ID Transacción:</strong> {self.transaction_id}</li>
                        <li><strong>Monto:</strong> {self.currency} {self.amount}</li>
                        <li><strong>Fecha:</strong> {self.completed_at}</li>
                    </ul>
                    """,
                    header="Pago Completado"
                )
    
    def send_failure_notification(self):
        """Enviar notificación de pago fallido"""
        if self.customer:
            customer_doc = frappe.get_doc("Customer", self.customer)
            if customer_doc.email_id:
                frappe.sendmail(
                    recipients=[customer_doc.email_id],
                    subject="Pago Fallido - USP Gateway",
                    message=f"""
                    <h3>Pago Fallido</h3>
                    <p>Su pago no pudo ser procesado:</p>
                    <ul>
                        <li><strong>ID Transacción:</strong> {self.transaction_id}</li>
                        <li><strong>Monto:</strong> {self.currency} {self.amount}</li>
                        <li><strong>Error:</strong> {self.error_message or 'Error desconocido'}</li>
                    </ul>
                    <p>Por favor, intente nuevamente o contacte con soporte.</p>
                    """,
                    header="Pago Fallido"
                )