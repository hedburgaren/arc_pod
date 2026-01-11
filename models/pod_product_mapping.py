# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PodProductMapping(models.Model):
    """Model for mapping Odoo products to POD provider products."""

    _name = 'pod.product.mapping'
    _description = 'POD Product Mapping'
    _order = 'odoo_product_id, provider_id'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        readonly=True,
    )
    odoo_product_id = fields.Many2one(
        comodel_name='product.template',
        string='Odoo Product',
        required=True,
        ondelete='cascade',
        index=True,
    )
    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='POD Provider',
        required=True,
        ondelete='cascade',
        index=True,
    )
    pod_product_id = fields.Char(
        string='POD Product ID',
        required=True,
        help='External product ID from POD provider',
    )
    pod_product_name = fields.Char(
        string='POD Product Name',
        readonly=True,
        help='Product name from POD provider',
    )
    pod_variant_id = fields.Char(
        string='POD Variant ID',
        help='External variant ID if applicable',
    )
    pod_sku = fields.Char(
        string='POD SKU',
        readonly=True,
        help='SKU from POD provider',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    last_sync = fields.Datetime(
        string='Last Sync',
        readonly=True,
        help='Last time product data was synced from provider',
    )

    _sql_constraints = [
        (
            'unique_mapping',
            'UNIQUE(odoo_product_id, provider_id)',
            'A product can only have one mapping per provider!'
        ),
    ]

    @api.depends('odoo_product_id', 'pod_product_name')
    def _compute_name(self):
        """Compute display name from Odoo product and POD product."""
        for record in self:
            if record.odoo_product_id and record.pod_product_name:
                record.name = f"{record.odoo_product_id.name} → {record.pod_product_name}"
            elif record.odoo_product_id:
                record.name = f"{record.odoo_product_id.name} → (Not synced)"
            else:
                record.name = _('Product Mapping')

    def name_get(self):
        """Return custom display name."""
        result = []
        for record in self:
            if record.odoo_product_id and record.pod_product_name:
                name = f"{record.odoo_product_id.name} → {record.pod_product_name}"
            elif record.odoo_product_id:
                name = f"{record.odoo_product_id.name} → (Not synced)"
            else:
                name = _('Product Mapping')
            result.append((record.id, name))
        return result

    def action_sync_from_provider(self):
        """
        Refresh product data from POD API.
        Fetches the latest product information and updates the mapping.
        """
        self.ensure_one()

        # Get API configuration
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')

        if not api_key:
            raise ValidationError(_('API key not configured. Please configure the API settings first.'))

        # Get provider details
        provider_code = self.provider_id.code
        api_url = self.provider_id.api_url

        try:
            # Import API clients
            from .printify_api import PrintifyAPI
            from .gelato_api import GelatoAPI
            from .printful_api import PrintfulAPI

            # Instantiate the appropriate API client
            if provider_code == 'printify':
                if not shop_id:
                    raise ValidationError(_('Shop ID not configured. Printify requires a Shop ID.'))
                api_client = PrintifyAPI(api_key=api_key, base_url=api_url)
            elif provider_code == 'gelato':
                api_client = GelatoAPI(api_key=api_key, base_url=api_url)
            elif provider_code == 'printful':
                api_client = PrintfulAPI(api_key=api_key, base_url=api_url)
            else:
                raise ValidationError(_('Unknown provider: %s') % provider_code)

            # Fetch products from provider
            _logger.info("Syncing product mapping from %s", provider_code)
            products = api_client.get_products()

            # Find matching product
            matching_product = None
            for product in products:
                if product.get('id') == self.pod_product_id:
                    matching_product = product
                    break

            if matching_product:
                # Update mapping with latest data
                self.write({
                    'pod_product_name': matching_product.get('name', ''),
                    'pod_sku': matching_product.get('sku', ''),
                    'last_sync': fields.Datetime.now(),
                })

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('Product data refreshed successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise ValidationError(_('Product not found in provider catalog'))

        except Exception as e:
            error_message = _('Failed to sync product: %s') % str(e)
            _logger.error(error_message, exc_info=True)

            # Log the error
            self.env['pod.error.log'].sudo().create({
                'provider_id': self.provider_id.id,
                'error_message': error_message,
                'error_code': '',
                'request_endpoint': 'sync_product_mapping',
                'timestamp': fields.Datetime.now(),
            })

            raise ValidationError(error_message)
