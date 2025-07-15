// gateway_usp/public/js/usp_payment_gateway.js

// Verificar que frappe esté disponible
if (typeof frappe === 'undefined') {
    console.warn('Frappe no está disponible, saltando inicialización USP');
} else {
    frappe.provide("gateway_usp");

    gateway_usp.PaymentGateway = class PaymentGateway {
        constructor(options) {
            this.options = options || {};
            this.initialized = false;
            this.init();
        }

        init() {
            if (this.initialized) return;
            
            try {
                this.setup_payment_integration();
                this.initialized = true;
                console.log('USP Gateway inicializado correctamente');
            } catch (error) {
                console.error('Error inicializando USP Gateway:', error);
                this.initialized = false;
            }
        }

        // Método para reinicializar si es necesario
        reinitialize() {
            this.initialized = false;
            this.init();
        }

        setup_payment_integration() {
            // Configuración básica - siempre disponible
            console.log('Configurando integración USP...');
        }

        setup_payment_request_integration() {
            const me = this;
            
            console.log('Configurando Payment Request para USP...');
            
            // Verificar datos básicos
            if (!frappe.route_options) {
                console.warn('No hay datos de ruta disponibles');
                me.show_new_card_form();
                return;
            }

            const customer = frappe.route_options.customer;
            if (!customer) {
                console.warn('No hay customer en route_options');
                me.show_new_card_form();
                return;
            }

            // Obtener tarjetas del cliente
            frappe.call({
                method: "gateway_usp.api.payment_controller.get_customer_cards",
                args: {
                    customer: customer
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        me.show_saved_cards(r.message);
                    } else {
                        me.show_new_card_form();
                    }
                },
                error: function(error) {
                    console.error('Error obteniendo tarjetas:', error);
                    me.show_new_card_form();
                }
            });
        }

        show_saved_cards(cards) {
            const me = this;
            
            const dialog = new frappe.ui.Dialog({
                title: __("Pagar con USP Gateway"),
                fields: [
                    {
                        label: __("Tarjetas Guardadas"),
                        fieldname: "saved_cards",
                        fieldtype: "HTML"
                    },
                    {
                        label: __("Usar Nueva Tarjeta"),
                        fieldname: "use_new_card",
                        fieldtype: "Check"
                    }
                ],
                primary_action_label: __("Pagar"),
                primary_action: function() {
                    const use_new = dialog.get_value('use_new_card');
                    if (use_new) {
                        dialog.hide();
                        me.show_new_card_form();
                    } else {
                        me.process_payment();
                        dialog.hide();
                    }
                }
            });

            let cards_html = '<div class="usp-saved-cards">';
            cards.forEach((card, index) => {
                const checked = index === 0 ? 'checked' : '';
                cards_html += `
                    <div class="card-option" data-token="${card.token}" style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                        <input type="radio" name="selected_card" value="${card.token}" ${checked}>
                        <label style="margin-left: 10px;">**** **** **** ${card.last_four} - ${card.brand} (${card.expiry})</label>
                    </div>
                `;
            });
            cards_html += '</div>';

            dialog.fields_dict.saved_cards.$wrapper.html(cards_html);
            dialog.show();
        }

        show_new_card_form() {
            const me = this;
            
            const dialog = new frappe.ui.Dialog({
                title: __("Nueva Tarjeta - USP Gateway"),
                fields: [
                    {
                        label: __("Número de Tarjeta"),
                        fieldname: "card_number",
                        fieldtype: "Data",
                        reqd: 1,
                        description: "Ingrese el número completo de la tarjeta"
                    },
                    {
                        label: __("Nombre del Titular"),
                        fieldname: "cardholder_name",
                        fieldtype: "Data",
                        reqd: 1
                    },
                    {
                        label: __("Mes de Vencimiento"),
                        fieldname: "expiry_month",
                        fieldtype: "Select",
                        options: "01\n02\n03\n04\n05\n06\n07\n08\n09\n10\n11\n12",
                        reqd: 1
                    },
                    {
                        label: __("Año de Vencimiento"),
                        fieldname: "expiry_year",
                        fieldtype: "Select",
                        options: this.get_year_options(),
                        reqd: 1
                    },
                    {
                        label: __("CVV"),
                        fieldname: "cvv",
                        fieldtype: "Data",
                        reqd: 1,
                        description: "Código de seguridad de 3 dígitos"
                    },
                    {
                        label: __("Guardar Tarjeta"),
                        fieldname: "save_card",
                        fieldtype: "Check",
                        description: "Guardar esta tarjeta para futuros pagos"
                    }
                ],
                primary_action_label: __("Procesar Pago"),
                primary_action: function() {
                    me.process_new_card_payment();
                    dialog.hide();
                }
            });

            dialog.show();
        }

        get_year_options() {
            const currentYear = new Date().getFullYear();
            let options = '';
            for (let i = 0; i < 10; i++) {
                const year = currentYear + i;
                options += `${year}\n`;
            }
            return options;
        }

        process_payment() {
            const me = this;
            const selected_card = $('input[name="selected_card"]:checked').val();
            
            if (!selected_card) {
                frappe.msgprint(__("Por favor seleccione una tarjeta"));
                return;
            }

            if (!frappe.route_options) {
                frappe.msgprint(__("Datos de pago no disponibles"));
                return;
            }

            frappe.show_progress(__('Procesando pago...'), 50);

            frappe.call({
                method: "gateway_usp.api.payment_controller.process_payment",
                args: {
                    payment_data: {
                        amount: frappe.route_options.amount,
                        currency: frappe.route_options.currency || "USD",
                        customer: frappe.route_options.customer,
                        card_token: selected_card,
                        reference_doctype: "Payment Request",
                        reference_docname: frappe.route_options.name
                    }
                },
                callback: function(r) {
                    frappe.hide_progress();
                    
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __("Pago Exitoso"),
                            message: __("Su pago ha sido procesado exitosamente"),
                            indicator: "green"
                        });
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    } else {
                        frappe.msgprint({
                            title: __("Error en el Pago"),
                            message: r.message?.message || __("Error al procesar el pago"),
                            indicator: "red"
                        });
                    }
                },
                error: function(error) {
                    frappe.hide_progress();
                    console.error('Error procesando pago:', error);
                    frappe.msgprint({
                        title: __("Error en el Pago"),
                        message: __("Error de conexión al procesar el pago"),
                        indicator: "red"
                    });
                }
            });
        }

        process_new_card_payment() {
            frappe.msgprint({
                title: __("Desarrollo"),
                message: __("Funcionalidad de nueva tarjeta en desarrollo. Contacte soporte."),
                indicator: "blue"
            });
        }
    };

    // Función para asegurar que el gateway esté disponible
    gateway_usp.ensure_gateway = function() {
        if (!window.usp_gateway || !window.usp_gateway.initialized) {
            console.log('Reinicializando USP Gateway...');
            window.usp_gateway = new gateway_usp.PaymentGateway();
        }
        return window.usp_gateway;
    };

    // Inicialización robusta
    $(document).ready(function() {
        if (typeof frappe !== 'undefined' && frappe.ready) {
            setTimeout(function() {
                try {
                    window.usp_gateway = new gateway_usp.PaymentGateway();
                    console.log('USP Gateway inicializado en document.ready');
                } catch (error) {
                    console.error('Error inicializando USP Gateway:', error);
                }
            }, 1000);
        }
    });
}

// Hooks mejorados para formularios
if (typeof frappe !== 'undefined' && frappe.ui && frappe.ui.form) {
    frappe.ui.form.on('Payment Request', {
        refresh: function(frm) {
            try {
                if (frm.doc.docstatus === 1 && frm.doc.status !== "Paid") {
                    frm.add_custom_button(__("Pagar con USP"), function() {
                        // Asegurar que el gateway esté disponible
                        const gateway = gateway_usp.ensure_gateway();
                        
                        if (gateway && gateway.initialized) {
                            gateway.setup_payment_request_integration();
                        } else {
                            frappe.msgprint({
                                title: __("Error"),
                                message: __("Error inicializando USP Gateway. Por favor recarga la página."),
                                indicator: "red"
                            });
                        }
                    });
                }
            } catch (error) {
                console.error('Error en Payment Request hook:', error);
                frappe.msgprint({
                    title: __("Error"),
                    message: __("Error configurando USP Gateway"),
                    indicator: "red"
                });
            }
        }
    });

    frappe.ui.form.on('Sales Invoice', {
        refresh: function(frm) {
            try {
                if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0) {
                    frm.add_custom_button(__("Pagar con USP"), function() {
                        frappe.show_progress(__('Creando Payment Request...'), 30);
                        
                        frappe.call({
                            method: "gateway_usp.utils.payment_utils.create_payment_request_with_usp",
                            args: {
                                doc: frm.doc.name,
                                amount: frm.doc.outstanding_amount,
                                currency: frm.doc.currency
                            },
                            callback: function(r) {
                                frappe.hide_progress();
                                
                                if (r.message) {
                                    frappe.set_route('Form', 'Payment Request', r.message.name);
                                } else {
                                    frappe.msgprint({
                                        title: __("Error"),
                                        message: __("No se pudo crear el Payment Request"),
                                        indicator: "red"
                                    });
                                }
                            },
                            error: function(r) {
                                frappe.hide_progress();
                                frappe.msgprint({
                                    title: __("Error"),
                                    message: r.message || __("Error creando Payment Request"),
                                    indicator: "red"
                                });
                            }
                        });
                    });
                }
            } catch (error) {
                console.error('Error en Sales Invoice hook:', error);
            }
        }
    });
}