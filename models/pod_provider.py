# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api, _


class PodProvider(models.Model):
    """Model representing print-on-demand service providers."""
    
    _name = 'pod.provider'
    _description = 'Print on Demand Provider'
    _order = 'name'

    name = fields.Char(
        string='Provider Name',
        required=True,
        translate=True,
    )
    code = fields.Selection(
        selection=[
            ('printify', 'Printify'),
            ('gelato', 'Gelato'),
            ('printful', 'Printful'),
        ],
        string='Provider Code',
        required=True,
    )
    api_url = fields.Char(
        string='API URL',
        readonly=True,
        compute='_compute_api_url',
        store=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    logo = fields.Binary(
        string='Logo',
        attachment=True,
    )

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Provider code must be unique!'),
    ]

    @api.depends('code')
    def _compute_api_url(self):
        """Compute the API URL based on the provider code."""
        for record in self:
            record.api_url = record._get_api_url()

    def _get_api_url(self):
        """
        Return the correct API URL based on provider code.
        
        Returns:
            str: Base API URL for the provider
        """
        url_mapping = {
            'printify': 'https://api.printify.com/v1/',
            'gelato': 'https://api.gelato.com/v1/',
            'printful': 'https://api.printful.com/',
        }
        return url_mapping.get(self.code, '')
