# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    'name': 'ARC POD - Print on Demand Integration',
    'version': '18.0.1.1.0',
    'category': 'Sales',
    'summary': 'Connect to Printify, Gelato, and Printful',
    'description': """
ARC POD - Print on Demand Integration
======================================

Connect your Odoo instance to popular print-on-demand services:
* Printify
* Gelato
* Printful

Features:
---------
* Configure API connections to POD providers
* Manage provider settings from Odoo
* Test API connections
* Map Odoo products to POD products
* Browse and sync product catalogs

    """,
    'author': 'hedburgaren',
    'website': 'https://github.com/hedburgaren/arc_pod',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/pod_provider_data.xml',
        'views/pod_provider_views.xml',
        'views/pod_config_views.xml',
        'views/pod_error_log_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
