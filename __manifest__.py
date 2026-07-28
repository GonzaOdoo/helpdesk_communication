# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Bridge',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': " Bridge for Helpdesk integration",
    'description': " Bridge for integrating Helpdesk with other modules",
    'author': 'GonzaOdoo',
    'maintainer': 'GonzaOdoo',
    'website': "https://www.github.com",
    'depends': ['mail','helpdesk'],
    'data': [
        'security/ir.model.access.csv',
        'views/helpdesk_bridge_link_views.xml',
        'views/helpdesk_bridge_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/reporte_ausencia_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
