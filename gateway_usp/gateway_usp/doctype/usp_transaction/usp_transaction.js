// Copyright (c) 2024, EduTech and contributors
// For license information, please see license.txt

frappe.ui.form.on('USP Transaction', {
    refresh: function(frm) {
        // Botón de reintento para transacciones fallidas
        if (frm.doc.status === 'Failed' || frm.doc.status === 'Cancelled') {
            frm.add_custom_button(__('Reintentar Pago'), function() {
                frm.call('retry_payment');
            }, __('Acciones'));
        }
        
        // Botón de cancelación para transacciones pendientes
        if (frm.doc.status === 'Pending' || frm.doc.status === 'Authorized') {
            frm.add_custom_button(__('Cancelar Transacción'), function() {
                frappe.confirm(
                    __('¿Está seguro de cancelar esta transacción?'),
                    function() {
                        frm.call('cancel_transaction');
                    }
                );
            }, __('Acciones'));
        }
        
        // Indicadores de estado
        frm.dashboard.clear_headline();
        
        if (frm.doc.status === 'Completed') {
            frm.dashboard.add_indicator(__('Completado'), 'green');
        } else if (frm.doc.status === 'Failed') {
            frm.dashboard.add_indicator(__('Fallido'), 'red');
        } else if (frm.doc.status === 'Pending') {
            frm.dashboard.add_indicator(__('Pendiente'), 'orange');
        } else if (frm.doc.status === 'Cancelled') {
            frm.dashboard.add_indicator(__('Cancelado'), 'grey');
        }
        
        // Mostrar enlace al documento relacionado
        if (frm.doc.reference_doctype && frm.doc.reference_docname) {
            frm.dashboard.add_comment(
                __('Documento relacionado: {0}', [
                    `<a href="/app/${frm.doc.reference_doctype.toLowerCase()}/${frm.doc.reference_docname}">${frm.doc.reference_docname}</a>`
                ]),
                'blue'
            );
        }
    }
});