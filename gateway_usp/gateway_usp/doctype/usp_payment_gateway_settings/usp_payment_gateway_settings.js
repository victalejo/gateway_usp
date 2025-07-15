// Copyright (c) 2024, EduTech and contributors
// For license information, please see license.txt

frappe.ui.form.on('USP Payment Gateway Settings', {
    refresh: function(frm) {
        // Limpiar botones existentes
        frm.clear_custom_buttons();
        
        // Botón para configurar datos de prueba
        frm.add_custom_button(__('Configurar Datos de Prueba'), function() {
            frappe.confirm(
                __('¿Configurar credenciales de prueba para desarrollo?'),
                function() {
                    frappe.call({
                        method: "gateway_usp.utils.setup_test_data.setup_test_credentials",
                        callback: function(r) {
                            frm.refresh();
                        }
                    });
                }
            );
        }, __('Desarrollo'));
        
        // Botones principales
        if (frm.doc.is_enabled) {
            // Grupo de Pruebas
            frm.add_custom_button(__('Probar Conexión'), function() {
                frm.call('test_connection');
            }, __('Pruebas'));
            
            frm.add_custom_button(__('Diagnósticos Completos'), function() {
                frm.call('run_diagnostics');
            }, __('Pruebas'));
            
            frm.add_custom_button(__('Página de Conectividad'), function() {
                window.open('/test_connectivity', '_blank');
            }, __('Pruebas'));
            
            // Grupo de Configuración
            frm.add_custom_button(__('Sincronizar'), function() {
                frm.call('sync_settings');
            }, __('Configuración'));
            
            // Botón de migración si es necesario
            if (frm.doc.merchant_id && !frm.doc.api_key) {
                frm.add_custom_button(__('Migrar a CROEM'), function() {
                    frappe.confirm(
                        __('¿Migrar configuración legacy a credenciales CROEM API Token v6.5?'),
                        function() {
                            frm.call('migrate_to_croem');
                        }
                    );
                }, __('Configuración'));
            }
        }
        
        // Mostrar indicadores de estado
        frm.dashboard.clear_headline();
        
        if (frm.doc.is_enabled) {
            if (frm.doc.use_mock_mode) {
                frm.dashboard.add_indicator(__('Gateway Habilitado (Mock)'), 'blue');
            } else {
                frm.dashboard.add_indicator(__('Gateway Habilitado'), 'green');
            }
            
            // Indicador de tipo de credenciales
            if (frm.doc.api_key) {
                frm.dashboard.add_indicator(__('Credenciales CROEM v6.5'), 'green');
            } else if (frm.doc.merchant_id) {
                frm.dashboard.add_indicator(__('Credenciales Legacy'), 'orange');
            }
            
            // Indicador de ambiente
            if (frm.doc.environment === 'PRODUCTION') {
                frm.dashboard.add_indicator(__('Producción'), 'red');
            } else {
                frm.dashboard.add_indicator(__('Sandbox'), 'yellow');
            }
        } else {
            frm.dashboard.add_indicator(__('Gateway Deshabilitado'), 'red');
        }
        
        // Mostrar información sobre documentación
        if (frm.doc.api_key) {
            frm.dashboard.set_headline(__('Basado en CROEM API Token v6.5'));
        }
    },
    
    is_enabled: function(frm) {
        if (frm.doc.is_enabled) {
            frappe.msgprint({
                title: __('Gateway Habilitado'),
                message: __('Configure las credenciales CROEM para mejor funcionalidad. Use modo Mock para testing.'),
                indicator: 'yellow'
            });
        }
    },
    
    use_mock_mode: function(frm) {
        if (frm.doc.use_mock_mode) {
            frappe.msgprint({
                title: __('Modo Mock Activado'),
                message: __('Las transacciones serán simuladas. No se procesarán pagos reales.'),
                indicator: 'blue'
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
                        message: __('Verifica que todas las credenciales CROEM sean correctas para producción'),
                        indicator: 'orange'
                    });
                },
                function() {
                    frm.set_value('environment', 'SANDBOX');
                }
            );
        }
    },
    
    // Validaciones para campos CROEM
    api_key: function(frm) {
        if (frm.doc.api_key && !frm.doc.access_code) {
            frappe.msgprint({
                title: __('Configuración CROEM'),
                message: __('Recuerda configurar también el Access Code'),
                indicator: 'yellow'
            });
        }
    },
    
    access_code: function(frm) {
        if (frm.doc.access_code && !frm.doc.api_key) {
            frappe.msgprint({
                title: __('Configuración CROEM'),
                message: __('Recuerda configurar también el API Key'),
                indicator: 'yellow'
            });
        }
    },
    
    merchant_account_number: function(frm) {
        if (frm.doc.merchant_account_number && !frm.doc.terminal_name) {
            frappe.msgprint({
                title: __('Configuración CROEM'),
                message: __('Recuerda configurar también el Terminal Name'),
                indicator: 'yellow'
            });
        }
    },
    
    // Función para mostrar ayuda
    setup: function(frm) {
        // Agregar help text dinámico
        frm.set_intro(__('Configuración de USP Payment Gateway basado en documentación CROEM API Token v6.5'));
        
        if (!frm.doc.is_enabled) {
            frm.set_intro(__('Habilite el gateway y configure las credenciales CROEM para comenzar'), 'blue');
        }
    }
});

// Validaciones personalizadas
frappe.ui.form.on('USP Payment Gateway Settings', 'validate', function(frm) {
    // Validar que si está habilitado, tenga al menos un conjunto de credenciales
    if (frm.doc.is_enabled) {
        const has_croem = frm.doc.api_key && frm.doc.access_code;
        const has_legacy = frm.doc.merchant_id && frm.doc.secret_key;
        
        if (!has_croem && !has_legacy) {
            frappe.validated = false;
            frappe.msgprint({
                title: __('Error de Validación'),
                message: __('Debe configurar credenciales CROEM (recomendado) o credenciales legacy'),
                indicator: 'red'
            });
        }
    }
});

// Función helper para mostrar documentación
function show_croem_help() {
    frappe.msgprint({
        title: __('Documentación CROEM'),
        message: __(`
            <strong>API Token v6.5</strong><br>
            - API Key: Llave única que identifica al comercio<br>
            - Access Code: Código de acceso del comercio<br>
            - Merchant Account Number: MID del Banco Adquirente<br>
            - Terminal Name: TID del Banco Adquirente<br><br>
            <strong>URLs:</strong><br>
            - Sandbox: tokenv2test.merchantprocess.net<br>
            - Producción: gateway.merchantprocess.net
        `),
        indicator: 'blue'
    });
}