import frappe
import os
import json

def create_doctypes():
    """Crear DocTypes automáticamente"""
    
    app_path = frappe.get_app_path("gateway_usp")
    doctypes_path = os.path.join(app_path, "gateway_usp", "doctype")
    
    # Lista de DocTypes a crear
    doctypes = [
        "usp_payment_gateway_settings",
        "usp_transaction",
        "usp_customer"
    ]
    
    for doctype_name in doctypes:
        doctype_path = os.path.join(doctypes_path, doctype_name, f"{doctype_name}.json")
        
        if os.path.exists(doctype_path):
            with open(doctype_path, 'r') as f:
                doctype_json = json.load(f)
                
            # Verificar si ya existe
            if not frappe.db.exists("DocType", doctype_json["name"]):
                doc = frappe.get_doc(doctype_json)
                doc.insert()
                print(f"DocType {doctype_json['name']} creado exitosamente")
            else:
                print(f"DocType {doctype_json['name']} ya existe")

# Ejecutar después de la instalación
def after_install():
    create_doctypes()
    print("Gateway USP: DocTypes instalados correctamente")