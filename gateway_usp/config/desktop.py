from frappe import _

def get_data():
    return [
        {
            "module_name": "Gateway USP",
            "color": "blue",
            "icon": "octicon octicon-credit-card",
            "type": "module",
            "label": _("Gateway USP"),
            "description": _("Pasarela de pagos XpressPago USP"),
            "hidden": 0
        }
    ]