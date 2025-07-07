// gateway_usp/public/js/usp_payment_gateway.js

frappe.provide("gateway_usp");

gateway_usp.PaymentGateway = class PaymentGateway {
    constructor(options) {
        this.options = options || {};
        this.init();
    }

    init() {
        this.setup_payment_button();
        this.bind_events();
    }

    setup_payment_button() {
        // Agregar botón de pago USP
        if (frappe.route_options && frappe.route_options.doctype === "Payment Request") {
            this.add_usp_payment_button();
        }
    }

    add_usp_payment_button() {
        const me = this;
        
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
            }
        });
    }

    show_saved_cards(cards) {
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
                this.process_payment();
            }
        });

        // Mostrar tarjetas guardadas
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
                this.process_new_card_payment();
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

        frappe.call({
            method: "gateway_usp.api.payment_controller.process_payment",
            args: {
                payment_data: {
                    amount: frappe.route_options.amount,
                    currency: frappe.route_options.currency,
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
            }
        });
    }

    bind_events() {
        // Eventos adicionales según necesidades
        $(document).on('change', 'input[name="selected_card"]', function() {
            $('.card-option').removeClass('selected');
            $(this).closest('.card-option').addClass('selected');
        });
    }
};

// Inicializar cuando el DOM esté listo
frappe.ready(function() {
    new gateway_usp.PaymentGateway();
});

// Agregar a hooks de formularios específicos
frappe.ui.form.on('Payment Request', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status !== "Paid") {
            frm.add_custom_button(__("Pagar con USP"), function() {
                new gateway_usp.PaymentGateway({
                    doc: frm.doc
                });
            });
        }
    }
});