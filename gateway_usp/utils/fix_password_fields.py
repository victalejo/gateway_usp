# gateway_usp/utils/fix_password_fields.py

import frappe

@frappe.whitelist()
def fix_password_fields():
    """Corregir campos de contraseña en USP Settings"""
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        
        # Verificar y corregir access_code
        if settings.get('access_code'):
            # Si hay valor en el campo, asegurar que esté guardado como contraseña
            try:
                existing_password = settings.get_password('access_code')
                if not existing_password:
                    settings.set_password('access_code', settings.get('access_code'))
                    frappe.msgprint("access_code corregido", indicator="green")
            except:
                settings.set_password('access_code', settings.get('access_code'))
                frappe.msgprint("access_code establecido como contraseña", indicator="green")
        
        # Verificar y corregir secret_key
        if settings.get('secret_key'):
            # Si hay valor en el campo, asegurar que esté guardado como contraseña
            try:
                existing_password = settings.get_password('secret_key')
                if not existing_password:
                    settings.set_password('secret_key', settings.get('secret_key'))
                    frappe.msgprint("secret_key corregido", indicator="green")
            except:
                settings.set_password('secret_key', settings.get('secret_key'))
                frappe.msgprint("secret_key establecido como contraseña", indicator="green")
        
        # Guardar cambios
        settings.save()
        frappe.db.commit()
        
        frappe.msgprint("Campos de contraseña corregidos exitosamente", indicator="green")
        
        return {"success": True, "message": "Campos corregidos"}
        
    except Exception as e:
        frappe.log_error(f"Error corrigiendo campos de contraseña: {str(e)}")
        frappe.msgprint(f"Error: {str(e)}", indicator="red")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def test_password_access():
    """Probar acceso a campos de contraseña"""
    try:
        settings = frappe.get_single("USP Payment Gateway Settings")
        
        results = {
            "access_code_field": bool(settings.get('access_code')),
            "access_code_password": False,
            "secret_key_field": bool(settings.get('secret_key')),
            "secret_key_password": False
        }
        
        # Probar access_code
        try:
            access_code = settings.get_password('access_code')
            results["access_code_password"] = bool(access_code)
            results["access_code_value"] = access_code[:5] + "..." if access_code else None
        except Exception as e:
            results["access_code_error"] = str(e)
        
        # Probar secret_key
        try:
            secret_key = settings.get_password('secret_key')
            results["secret_key_password"] = bool(secret_key)
            results["secret_key_value"] = secret_key[:5] + "..." if secret_key else None
        except Exception as e:
            results["secret_key_error"] = str(e)
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error probando acceso a contraseñas: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    fix_password_fields() 