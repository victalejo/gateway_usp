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

        // Mejorar el formulario de nueva tarjeta
        show_new_card_form() {
            const me = this;
            
            const dialog = new frappe.ui.Dialog({
                title: __("Pagar con Nueva Tarjeta"),
                fields: [
                    {
                        label: __("Número de Tarjeta"),
                        fieldname: "card_number",
                        fieldtype: "Data",
                        reqd: 1,
                        placeholder: "1234 5678 9012 3456",
                        change: function() {
                            // Formatear número de tarjeta
                            let value = this.get_value().replace(/\s/g, '');
                            let formatted = value.replace(/(.{4})/g, '$1 ').trim();
                            this.set_value(formatted);
                            
                            // Detectar tipo de tarjeta
                            me.detect_card_type(value);
                        }
                    },
                    {
                        label: __("Nombre del Titular"),
                        fieldname: "cardholder_name",
                        fieldtype: "Data",
                        reqd: 1,
                        placeholder: "Como aparece en la tarjeta"
                    },
                    {
                        fieldtype: "Column Break"
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
                        placeholder: "123"
                    },
                    {
                        fieldtype: "Section Break"
                    },
                    {
                        label: __("Guardar Tarjeta"),
                        fieldname: "save_card",
                        fieldtype: "Check",
                        description: __("Guardar esta tarjeta para futuros pagos")
                    },
                    {
                        fieldtype: "HTML",
                        fieldname: "card_info",
                        options: `
                            <div class="card-info" style="margin-top: 10px;">
                                <div class="card-type" style="font-weight: bold; margin-bottom: 5px;"></div>
                                <div class="security-info" style="color: #666; font-size: 12px;">
                                    <i class="fa fa-lock"></i> Sus datos están protegidos con encriptación SSL
                                </div>
                            </div>
                        `
                    }
                ],
                primary_action_label: __("Procesar Pago"),
                primary_action: function() {
                    me.process_new_card_payment();
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

        // Función para detectar tipo de tarjeta
        detect_card_type(card_number) {
            const cleaned = card_number.replace(/[\s-]/g, '');
            let card_type = "Desconocida";
            
            // Patrones para diferentes tipos de tarjetas
            const patterns = {
                'Visa': /^4/,
                'Mastercard': /^5[1-5]/,
                'American Express': /^3[47]/,
                'Discover': /^6(?:011|5)/,
                'Diners Club': /^3[0689]/,
                'JCB': /^35/
            };
            
            for (const [type, pattern] of Object.entries(patterns)) {
                if (pattern.test(cleaned)) {
                    card_type = type;
                    break;
                }
            }
            
            // Actualizar UI
            const card_info = cur_dialog.fields_dict.card_info.$wrapper.find('.card-type');
            card_info.text(`Tipo: ${card_type}`);
        }

        // Función para validar número de tarjeta (algoritmo de Luhn)
        validate_card_number(card_number) {
            // Remover espacios y guiones
            const cleaned = card_number.replace(/[\s-]/g, '');
            
            // Debe contener solo números
            if (!/^\d+$/.test(cleaned)) {
                return false;
            }
            
            // Debe tener entre 13 y 19 dígitos
            if (cleaned.length < 13 || cleaned.length > 19) {
                return false;
            }
            
            // Algoritmo de Luhn
            let sum = 0;
            let shouldDouble = false;
            
            for (let i = cleaned.length - 1; i >= 0; i--) {
                let digit = parseInt(cleaned.charAt(i));
                
                if (shouldDouble) {
                    digit *= 2;
                    if (digit > 9) {
                        digit -= 9;
                    }
                }
                
                sum += digit;
                shouldDouble = !shouldDouble;
            }
            
            return sum % 10 === 0;
        }

        // Reemplazar la función process_new_card_payment existente
        process_new_card_payment() {
            const me = this;
            
            // Obtener datos del formulario
            const dialog = cur_dialog;
            const values = dialog.get_values();
            
            // Validar datos requeridos
            if (!values.card_number || !values.cardholder_name || !values.expiry_month || 
                !values.expiry_year || !values.cvv) {
                frappe.msgprint(__("Todos los campos son obligatorios"));
                return;
            }
            
            // Validar número de tarjeta (básico)
            if (!me.validate_card_number(values.card_number)) {
                frappe.msgprint(__("Número de tarjeta inválido"));
                return;
            }
            
            // Validar CVV
            if (values.cvv.length < 3 || values.cvv.length > 4) {
                frappe.msgprint(__("CVV inválido"));
                return;
            }
            
            // Mostrar indicador de carga
            frappe.show_progress(__("Procesando pago"), 30, 100, __("Validando tarjeta..."));
            
            // Preparar datos para el pago
            const payment_data = {
                // Datos del pago
                amount: frappe.route_options.amount,
                currency: frappe.route_options.currency || "USD",
                customer: frappe.route_options.customer,
                reference_doctype: "Payment Request",
                reference_docname: frappe.route_options.name,
                
                // Datos de la nueva tarjeta
                card_data: {
                    card_number: values.card_number.replace(/\s/g, ''), // Remover espacios
                    cardholder_name: values.cardholder_name,
                    expiry_month: values.expiry_month,
                    expiry_year: values.expiry_year,
                    cvv: values.cvv,
                    save_card: values.save_card || false
                }
            };
            
            // Procesar pago con nueva tarjeta
            frappe.call({
                method: "gateway_usp.api.payment_controller.process_payment_with_new_card",
                args: {
                    payment_data: payment_data
                },
                callback: function(r) {
                    frappe.hide_progress();
                    
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __("Pago Exitoso"),
                            message: __("Su pago ha sido procesado exitosamente. ID: {0}", [r.message.transaction_id]),
                            indicator: "green"
                        });
                        
                        setTimeout(() => {
                            window.location.reload();
                        }, 3000);
                    } else {
                        frappe.msgprint({
                            title: __("Error en el Pago"),
                            message: r.message.message || __("Error al procesar el pago"),
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