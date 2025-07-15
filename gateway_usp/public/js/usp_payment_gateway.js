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
            this.card_validation_timeout = null; // NUEVO: Para evitar múltiples validaciones
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
            
            // NUEVO: Función para obtener datos del cliente de múltiples fuentes
            function getCustomerData() {
                let customer_data = {};
                
                // Fuente 1: frappe.route_options
                if (frappe.route_options) {
                    customer_data = {
                        customer: frappe.route_options.customer || frappe.route_options.party,
                        customer_name: frappe.route_options.customer_name,
                        amount: frappe.route_options.amount || frappe.route_options.grand_total,
                        currency: frappe.route_options.currency || "USD",
                        reference_doctype: frappe.route_options.reference_doctype,
                        reference_docname: frappe.route_options.reference_docname || frappe.route_options.name
                    };
                }
                
                // Fuente 2: localStorage como respaldo
                if (!customer_data.customer) {
                    const stored_data = localStorage.getItem('usp_payment_data');
                    if (stored_data) {
                        try {
                            const parsed_data = JSON.parse(stored_data);
                            customer_data = {
                                customer: parsed_data.customer || parsed_data.party,
                                customer_name: parsed_data.customer_name,
                                amount: parsed_data.amount || parsed_data.grand_total,
                                currency: parsed_data.currency || "USD",
                                reference_doctype: parsed_data.reference_doctype,
                                reference_docname: parsed_data.reference_docname || parsed_data.name
                            };
                        } catch (e) {
                            console.error('Error parsing stored payment data:', e);
                        }
                    }
                }
                
                // Fuente 3: cur_frm como último recurso
                if (!customer_data.customer && cur_frm && cur_frm.doc) {
                    customer_data = {
                        customer: cur_frm.doc.party || cur_frm.doc.customer,
                        customer_name: cur_frm.doc.customer_name,
                        amount: cur_frm.doc.grand_total,
                        currency: cur_frm.doc.currency || "USD",
                        reference_doctype: "Payment Request",
                        reference_docname: cur_frm.doc.name
                    };
                }
                
                return customer_data;
            }
            
            // Obtener datos del cliente
            const customer_data = getCustomerData();
            
            console.log('Datos del cliente obtenidos:', customer_data);
            
            // Validar que tenemos datos del cliente
            if (!customer_data.customer) {
                console.warn('No se encontraron datos del cliente');
                frappe.msgprint({
                    title: __("Error"),
                    message: __("No se encontraron datos del cliente. Por favor, recarga la página."),
                    indicator: "orange"
                });
                me.show_new_card_form();
                return;
            }
            
            // Guardar datos del cliente en la instancia
            me.customer_data = customer_data;
            
            // Obtener tarjetas del cliente
            frappe.call({
                method: "gateway_usp.api.payment_controller.get_customer_cards",
                args: {
                    customer: customer_data.customer
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
                            // CORREGIDO: Evitar múltiples llamadas
                            if (me.card_validation_timeout) {
                                clearTimeout(me.card_validation_timeout);
                            }
                            
                            me.card_validation_timeout = setTimeout(() => {
                                const value = this.get_value();
                                if (value) {
                                    me.format_and_detect_card(this, value);
                                }
                            }, 300); // Esperar 300ms después de que el usuario deje de escribir
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
                        placeholder: "123",
                        change: function() {
                            // Limitar CVV a 3-4 dígitos
                            const value = this.get_value();
                            if (value && value.length > 4) {
                                this.set_value(value.substring(0, 4));
                            }
                        }
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
                                <div class="card-type" style="font-weight: bold; margin-bottom: 5px; color: #2196F3;"></div>
                                <div class="security-info" style="color: #666; font-size: 12px;">
                                    <i class="fa fa-lock"></i> Sus datos están protegidos con encriptación SSL
                                </div>
                            </div>
                        `
                    },
                    {
                        fieldtype: "Section Break"
                    },
                    {
                        fieldtype: "HTML",
                        fieldname: "debug_info",
                        options: `
                            <div style="margin-top: 10px;">
                                <button type="button" class="btn btn-xs btn-default" onclick="window.usp_gateway.debug_payment_data()">
                                    Debug Info
                                </button>
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
            
            // Referencia al diálogo para uso posterior
            this.current_dialog = dialog;
        }

        // CORREGIDO: Función para formatear y detectar tarjeta
        format_and_detect_card(field, value) {
            try {
                // Remover espacios existentes
                let cleaned = value.replace(/\s/g, '');
                
                // Validar que solo contenga números
                if (!/^\d*$/.test(cleaned)) {
                    cleaned = cleaned.replace(/\D/g, '');
                }
                
                // Limitar a 19 dígitos máximo
                if (cleaned.length > 19) {
                    cleaned = cleaned.substring(0, 19);
                }
                
                // Formatear con espacios cada 4 dígitos
                let formatted = cleaned.replace(/(.{4})/g, '$1 ').trim();
                
                // Actualizar el campo solo si es diferente para evitar bucles
                if (field.get_value() !== formatted) {
                    field.set_value(formatted);
                }
                
                // Detectar tipo de tarjeta
                this.detect_card_type(cleaned);
                
            } catch (error) {
                console.error('Error formateando tarjeta:', error);
            }
        }

        // CORREGIDO: Función para detectar tipo de tarjeta
        detect_card_type(card_number) {
            try {
                if (!card_number || card_number.length < 4) {
                    this.update_card_type_display("Desconocida");
                    return;
                }
                
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
                    if (pattern.test(card_number)) {
                        card_type = type;
                        break;
                    }
                }
                
                this.update_card_type_display(card_type);
                
            } catch (error) {
                console.error('Error detectando tipo de tarjeta:', error);
                this.update_card_type_display("Error");
            }
        }

        // NUEVA: Función para actualizar la UI del tipo de tarjeta
        update_card_type_display(card_type) {
            try {
                if (this.current_dialog) {
                    const card_info = this.current_dialog.fields_dict.card_info.$wrapper.find('.card-type');
                    if (card_info.length) {
                        card_info.text(`Tipo: ${card_type}`);
                        
                        // Cambiar color según el tipo
                        const color = card_type === "Desconocida" ? "#999" : "#2196F3";
                        card_info.css('color', color);
                    }
                }
            } catch (error) {
                console.error('Error actualizando tipo de tarjeta:', error);
            }
        }

        get_year_options() {
            const currentYear = new Date().getFullYear();
            let options = '';
            for (let i = 0; i < 15; i++) {
                const year = currentYear + i;
                options += `${year}\n`;
            }
            return options;
        }

        // CORREGIDO: Validación de tarjeta mejorada
        validate_card_number(card_number) {
            try {
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
                
            } catch (error) {
                console.error('Error validando tarjeta:', error);
                return false;
            }
        }

        // MEJORADO: Procesamiento de pago con nueva tarjeta
        process_new_card_payment() {
            const me = this;
            
            try {
                // Obtener datos del formulario
                const dialog = me.current_dialog;
                const values = dialog.get_values();
                
                // Validar datos requeridos
                if (!values.card_number || !values.cardholder_name || !values.expiry_month || 
                    !values.expiry_year || !values.cvv) {
                    frappe.msgprint(__("Todos los campos son obligatorios"));
                    return;
                }
                
                // NUEVO: Obtener datos del cliente de múltiples fuentes
                let customer_data = me.customer_data;
                
                if (!customer_data) {
                    // Intentar obtener de frappe.route_options
                    customer_data = {
                        customer: frappe.route_options?.customer || frappe.route_options?.party,
                        amount: frappe.route_options?.amount || frappe.route_options?.grand_total,
                        currency: frappe.route_options?.currency || "USD",
                        reference_doctype: frappe.route_options?.reference_doctype || "Payment Request",
                        reference_docname: frappe.route_options?.reference_docname || frappe.route_options?.name
                    };
                }
                
                // Si aún no tenemos datos, intentar desde localStorage
                if (!customer_data.customer) {
                    const stored_data = localStorage.getItem('usp_payment_data');
                    if (stored_data) {
                        try {
                            const parsed_data = JSON.parse(stored_data);
                            customer_data = {
                                customer: parsed_data.customer || parsed_data.party,
                                amount: parsed_data.amount || parsed_data.grand_total,
                                currency: parsed_data.currency || "USD",
                                reference_doctype: parsed_data.reference_doctype || "Payment Request",
                                reference_docname: parsed_data.reference_docname || parsed_data.name
                            };
                        } catch (e) {
                            console.error('Error parsing stored data:', e);
                        }
                    }
                }
                
                // Validar que tenemos datos del cliente
                if (!customer_data.customer) {
                    frappe.msgprint({
                        title: __("Error de Validación"),
                        message: __("No se encontraron datos del cliente. Por favor, recarga la página e intenta nuevamente."),
                        indicator: "red"
                    });
                    console.error("Datos disponibles:", {
                        route_options: frappe.route_options,
                        customer_data: me.customer_data,
                        stored_data: localStorage.getItem('usp_payment_data')
                    });
                    return;
                }
                
                // Validar amount
                const amount = parseFloat(customer_data.amount);
                if (!amount || amount <= 0) {
                    frappe.msgprint({
                        title: __("Error de Validación"),
                        message: __("Monto inválido: {0}", [customer_data.amount]),
                        indicator: "red"
                    });
                    return;
                }
                
                // Validar número de tarjeta
                if (!me.validate_card_number(values.card_number)) {
                    frappe.msgprint(__("Número de tarjeta inválido"));
                    return;
                }
                
                // Validar CVV
                if (values.cvv.length < 3 || values.cvv.length > 4 || !/^\d+$/.test(values.cvv)) {
                    frappe.msgprint(__("CVV inválido"));
                    return;
                }
                
                // Validar fecha de vencimiento
                const currentYear = new Date().getFullYear();
                const currentMonth = new Date().getMonth() + 1;
                const expYear = parseInt(values.expiry_year);
                const expMonth = parseInt(values.expiry_month);
                
                if (expYear < currentYear || (expYear === currentYear && expMonth < currentMonth)) {
                    frappe.msgprint(__("Tarjeta vencida"));
                    return;
                }
                
                // Cerrar diálogo
                dialog.hide();
                
                // Mostrar indicador de carga
                frappe.show_progress(__("Procesando pago"), 30, 100, __("Validando datos..."));
                
                // Preparar datos para el pago
                const payment_data = {
                    amount: amount,
                    currency: customer_data.currency,
                    customer: customer_data.customer,
                    reference_doctype: customer_data.reference_doctype,
                    reference_docname: customer_data.reference_docname,
                    
                    card_data: {
                        card_number: values.card_number.replace(/\s/g, ''),
                        cardholder_name: values.cardholder_name,
                        expiry_month: values.expiry_month,
                        expiry_year: values.expiry_year,
                        cvv: values.cvv,
                        save_card: values.save_card || false
                    }
                };
                
                // Log para debug
                console.log("Datos del pago final:", payment_data);
                
                // Procesar pago
                frappe.call({
                    method: "gateway_usp.api.payment_controller.process_payment_with_new_card",
                    args: {
                        payment_data: payment_data
                    },
                    callback: function(r) {
                        frappe.hide_progress();
                        
                        if (r.message && r.message.success) {
                            // Limpiar localStorage
                            localStorage.removeItem('usp_payment_data');
                            
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
                
            } catch (error) {
                console.error('Error en process_new_card_payment:', error);
                frappe.msgprint({
                    title: __("Error"),
                    message: __("Error procesando el pago"),
                    indicator: "red"
                });
            }
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

        // NUEVO: Función de debug para verificar datos
        debug_payment_data() {
            const debug_info = {
                route_options: frappe.route_options,
                customer_data: this.customer_data,
                stored_data: localStorage.getItem('usp_payment_data'),
                current_form: cur_frm ? {
                    doctype: cur_frm.doc.doctype,
                    name: cur_frm.doc.name,
                    party: cur_frm.doc.party,
                    customer: cur_frm.doc.customer,
                    grand_total: cur_frm.doc.grand_total
                } : null,
                timestamp: new Date().toISOString()
            };
            
            console.log("=== DEBUG PAYMENT DATA ===");
            console.log(debug_info);
            console.log("=========================");
            
            frappe.msgprint({
                title: __("Debug Info"),
                message: `<pre>${JSON.stringify(debug_info, null, 2)}</pre>`,
                indicator: "blue"
            });
            
            return debug_info;
        }
    };

    // Función para asegurar que el gateway esté disponible
    gateway_usp.ensure_gateway = function() {
        if (!window.usp_gateway || !window.usp_gateway.initialized) {
            console.log('Inicializando USP Gateway...');
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

// Hooks para formularios
if (typeof frappe !== 'undefined' && frappe.ui && frappe.ui.form) {
    frappe.ui.form.on('Payment Request', {
        refresh: function(frm) {
            try {
                if (frm.doc.docstatus === 1 && frm.doc.status !== "Paid") {
                    frm.add_custom_button(__("Pagar con USP"), function() {
                        
                        // NUEVO: Preparar datos del cliente desde el Payment Request
                        const customer_data = {
                            customer: frm.doc.party,
                            customer_name: frm.doc.party_name,
                            amount: frm.doc.grand_total,
                            currency: frm.doc.currency,
                            reference_doctype: frm.doc.doctype,
                            reference_docname: frm.doc.name
                        };
                        
                        // Validar datos
                        if (!customer_data.customer) {
                            frappe.msgprint({
                                title: __("Error"),
                                message: __("No se encontró información del cliente en el Payment Request"),
                                indicator: "red"
                            });
                            return;
                        }
                        
                        // Guardar en localStorage
                        localStorage.setItem('usp_payment_data', JSON.stringify(customer_data));
                        
                        // Establecer route_options
                        frappe.route_options = customer_data;
                        
                        // Obtener gateway y configurar
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
            }
        }
    });

    frappe.ui.form.on('Sales Invoice', {
        refresh: function(frm) {
            try {
                if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0) {
                    frm.add_custom_button(__("Pagar con USP"), function() {
                        
                        // NUEVO: Validar datos antes de proceder
                        if (!frm.doc.customer) {
                            frappe.msgprint({
                                title: __("Error"),
                                message: __("No se encontró información del cliente en la factura"),
                                indicator: "red"
                            });
                            return;
                        }
                        
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
                                    // NUEVO: Establecer datos completos de ruta
                                    const payment_route_data = {
                                        name: r.message.name,
                                        amount: frm.doc.outstanding_amount,
                                        currency: frm.doc.currency,
                                        customer: frm.doc.customer,
                                        customer_name: frm.doc.customer_name || frm.doc.customer,
                                        reference_doctype: frm.doc.doctype,
                                        reference_docname: frm.doc.name,
                                        party: frm.doc.customer,
                                        grand_total: frm.doc.outstanding_amount,
                                        // Datos adicionales para debugging
                                        contact_email: frm.doc.contact_email,
                                        contact_person: frm.doc.contact_person,
                                        territory: frm.doc.territory
                                    };
                                    
                                    // Guardar en localStorage como respaldo
                                    localStorage.setItem('usp_payment_data', JSON.stringify(payment_route_data));
                                    
                                    // Establecer route_options
                                    frappe.route_options = payment_route_data;
                                    
                                    // Log para debug
                                    console.log("Datos de pago establecidos:", payment_route_data);
                                    
                                    // Navegar al Payment Request
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