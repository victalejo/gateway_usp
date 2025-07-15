// gateway_usp/public/js/usp_payment_gateway.js

// Verificar que frappe esté disponible antes de continuar
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
            // Solo inicializar una vez
            if (this.initialized) return;
            
            try {
                this.setup_payment_integration();
                this.initialized = true;
            } catch (error) {
                console.error('Error inicializando USP Gateway:', error);
            }
        }

        setup_payment_integration() {
            const me = this;
            
            // Solo ejecutar en contextos específicos
            if (!this.should_initialize()) {
                return;
            }

            // Configurar según el contexto
            if (frappe.route_options && frappe.route_options.doctype === "Payment Request") {
                this.setup_payment_request_integration();
            }
        }

        should_initialize() {
            // Verificar si estamos en un contexto apropiado
            const current_route = frappe.get_route();
            const valid_contexts = ['Form', 'payment-request', 'sales-invoice'];
            
            return current_route && current_route.some(route => 
                valid_contexts.some(context => route.includes(context))
            );
        }

        setup_payment_request_integration() {
            const me = this;
            
            // Solo proceder si tenemos datos de ruta válidos
            if (!frappe.route_options || !frappe.route_options.customer) {
                return;
            }

            frappe.call({
                method: "gateway_usp.api.payment_controller.get_customer_cards",
                args: {
                    customer: frappe.route_options.customer
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
                    me.process_payment.call(me);
                    dialog.hide();
                }
            });

            let cards_html = '<div class="usp-saved-cards">';
            cards.forEach(card => {
                cards_html += `
                    <div class="card-option" data-token="${card.token}">
                        <input type="radio" name="selected_card" value="${card.token}">
                        <label>**** **** **** ${card.last_four} - ${card.brand} (${card.expiry})</label>
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
                title: __("Pagar con USP Gateway"),
                fields: [
                    {
                        label: __("Número de Tarjeta"),
                        fieldname: "card_number",
                        fieldtype: "Data",
                        reqd: 1
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
                        reqd: 1
                    },
                    {
                        label: __("Guardar Tarjeta"),
                        fieldname: "save_card",
                        fieldtype: "Check"
                    }
                ],
                primary_action_label: __("Pagar"),
                primary_action: function() {
                    me.process_new_card_payment.call(me);
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
                            message: r.message.message || __("Error al procesar el pago"),
                            indicator: "red"
                        });
                    }
                },
                error: function(error) {
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
            // Implementar lógica para nueva tarjeta
            frappe.msgprint(__("Funcionalidad de nueva tarjeta en desarrollo"));
        }
    };

    // Inicialización controlada - solo cuando frappe esté completamente cargado
    $(document).ready(function() {
        // Verificar que estamos en un contexto apropiado
        if (typeof frappe !== 'undefined' && frappe.ready) {
            // Usar setTimeout para asegurar que frappe esté completamente inicializado
            setTimeout(function() {
                try {
                    window.usp_gateway = new gateway_usp.PaymentGateway();
                } catch (error) {
                    console.error('Error inicializando USP Gateway:', error);
                }
            }, 1000);
        }
    });
}

// Hooks específicos para formularios - solo ejecutar si frappe está disponible
if (typeof frappe !== 'undefined' && frappe.ui && frappe.ui.form) {
    frappe.ui.form.on('Payment Request', {
        refresh: function(frm) {
            try {
                if (frm.doc.docstatus === 1 && frm.doc.status !== "Paid") {
                    frm.add_custom_button(__("Pagar con USP"), function() {
                        if (window.usp_gateway) {
                            window.usp_gateway.setup_payment_request_integration();
                        } else {
                            frappe.msgprint(__("Gateway USP no disponible"));
                        }
                    });
                }
            } catch (error) {
                console.error('Error en Payment Request hook:', error);
            }
        }
    });

    frappe.ui.form.on('Sales Invoice', {
        refresh: function(frm) {
            try {
                if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0) {
                    frm.add_custom_button(__("Pagar con USP"), function() {
                        // Crear Payment Request con USP
                        frappe.call({
                            method: "gateway_usp.utils.payment_utils.create_payment_request_with_usp",
                            args: {
                                doc: frm.doc.name,  // Enviar solo el nombre del documento
                                amount: frm.doc.outstanding_amount,
                                currency: frm.doc.currency
                            },
                            callback: function(r) {
                                if (r.message) {
                                    frappe.set_route('Form', 'Payment Request', r.message.name);
                                }
                            },
                            error: function(r) {
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