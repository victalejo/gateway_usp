// Copyright (c) 2024, EduTech and contributors
// For license information, please see license.txt

frappe.ui.form.on('USP Payment Gateway Settings', {
    refresh: function(frm) {
        // Agregar botón de prueba de conexión
        if (frm.doc.is_enabled) {
            frm.add_custom_button(__('Probar Conexión'), function() {
                frm.call('test_connection');
            });
            
            frm.add_custom_button(__('Sincronizar'), function() {
                frm.call('sync_settings');
            });
        }
        
        // Mostrar indicador de estado
        if (frm.doc.is_enabled) {
            frm.dashboard.add_indicator(__('Gateway Habilitado'), 'green');
        } else {
            frm.dashboard.add_indicator(__('Gateway Deshabilitado'), 'red');
        }
    },
    
    is_enabled: function(frm) {
        if (frm.doc.is_enabled) {
            frappe.msgprint({
                title: __('Gateway Habilitado'),
                message: __('Recuerda configurar todos los campos requeridos'),
                indicator: 'yellow'
            });
        }
    },
    
    environment: function(frm) {
        if (frm.doc.environment === 'PRODUCTION') {
            frappe.confirm(
                __('¿Estás seguro de cambiar a ambiente de PRODUCCIÓN?'),
                function() {
                    frappe.msgprint({
                        title: __('Ambiente de Producción'),
                        message: __('Verifica que todas las credenciales sean correctas'),
                        indicator: 'orange'
                    });
                },
                function() {
                    frm.set_value('environment', 'SANDBOX');
                }
            );
        }
    }
});