# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PodCatalogWizard(models.TransientModel):
    """Wizard for browsing POD product catalogs and creating mappings."""

    _name = 'pod.catalog.wizard'
    _description = 'POD Catalog Wizard'

    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='Provider',
        required=True,
        help='Select the POD provider to fetch products from',
    )
    catalog_ids = fields.One2many(
        comodel_name='pod.product.catalog',
        inverse_name='wizard_id',
        string='Products',
        help='Available products from the provider',
    )
    selected_catalog_id = fields.Many2one(
        comodel_name='pod.product.catalog',
        string='Selected Product',
        help='Product selected to create mapping',
    )
    odoo_product_id = fields.Many2one(
        comodel_name='product.template',
        string='Odoo Product',
        required=True,
        help='Odoo product to map to POD product',
    )
    catalog_loaded = fields.Boolean(
        string='Catalog Loaded',
        default=False,
        help='Indicates if catalog has been fetched',
    )

    def action_fetch_catalog(self):
        """
        Fetch products from the selected provider's catalog.
        Populates the catalog_ids field with available products.
        """
        self.ensure_one()

        # Validate provider is selected
        if not self.provider_id:
            raise ValidationError(_('Please select a provider first.'))

        # Get API configuration
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        api_key = IrConfigParameter.get_param('arc_pod.api_key', default='')
        shop_id = IrConfigParameter.get_param('arc_pod.shop_id', default='')

        if not api_key:
            raise ValidationError(
                _('API key not configured. Please configure the API settings in Settings > ARC POD.')
            )

        # Get provider details
        provider_code = self.provider_id.code
        api_url = self.provider_id.api_url

        try:
            # Import API clients
            from ..models.printify_api import PrintifyAPI
            from ..models.gelato_api import GelatoAPI
            from ..models.printful_api import PrintfulAPI

            # Instantiate the appropriate API client
            if provider_code == 'printify':
                if not shop_id:
                    raise ValidationError(
                        _('Shop ID not configured. Printify requires a Shop ID. '
                          'Please configure it in Settings > ARC POD.')
                    )
                api_client = PrintifyAPI(api_key=api_key, base_url=api_url)
                products = api_client.get_products(shop_id=shop_id)
            elif provider_code == 'gelato':
                api_client = GelatoAPI(api_key=api_key, base_url=api_url)
                products = api_client.get_products()
            elif provider_code == 'printful':
                api_client = PrintfulAPI(api_key=api_key, base_url=api_url)
                products = api_client.get_products()
            else:
                raise ValidationError(_('Unknown provider: %s') % provider_code)

            # Clear existing catalog items for this wizard
            self.catalog_ids.unlink()

            # Create catalog entries
            catalog_records = []
            for product in products:
                catalog_record = self.env['pod.product.catalog'].create({
                    'wizard_id': self.id,
                    'provider_id': self.provider_id.id,
                    'product_id': product.get('id', ''),
                    'name': product.get('name', ''),
                    'description': product.get('description', ''),
                    'sku': product.get('sku', ''),
                    'variants': json.dumps(product.get('variants', [])),
                    'thumbnail_url': product.get('thumbnail_url', ''),
                })
                catalog_records.append(catalog_record.id)

            # Update wizard state
            self.write({
                'catalog_loaded': True,
            })

            _logger.info("Successfully fetched %d products from %s", len(products), provider_code)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Fetched %d products from %s') % (len(products), self.provider_id.name),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except ValidationError:
            raise
        except Exception as e:
            error_message = _('Failed to fetch catalog: %s') % str(e)
            _logger.error(error_message, exc_info=True)

            # Log the error
            self.env['pod.error.log'].sudo().create({
                'provider_id': self.provider_id.id,
                'error_message': error_message,
                'error_code': '',
                'request_endpoint': 'fetch_catalog',
                'timestamp': fields.Datetime.now(),
            })

            raise ValidationError(error_message)

    def action_create_mapping(self):
        """
        Create a product mapping based on the selected catalog item.
        Validates the selection and creates a pod.product.mapping record.
        """
        self.ensure_one()

        # Validate selection
        if not self.selected_catalog_id:
            raise ValidationError(_('Please select a product from the catalog.'))

        # Check if mapping already exists
        existing_mapping = self.env['pod.product.mapping'].search([
            ('odoo_product_id', '=', self.odoo_product_id.id),
            ('provider_id', '=', self.provider_id.id),
        ], limit=1)

        if existing_mapping:
            raise ValidationError(
                _('A mapping already exists for this product and provider. '
                  'Please edit the existing mapping or delete it first.')
            )

        # Create the mapping
        mapping = self.env['pod.product.mapping'].create({
            'odoo_product_id': self.odoo_product_id.id,
            'provider_id': self.provider_id.id,
            'pod_product_id': self.selected_catalog_id.product_id,
            'pod_product_name': self.selected_catalog_id.name,
            'pod_sku': self.selected_catalog_id.sku,
            'last_sync': fields.Datetime.now(),
        })

        _logger.info(
            "Created mapping: %s -> %s (%s)",
            self.odoo_product_id.name,
            self.selected_catalog_id.name,
            self.provider_id.name
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Product mapping created successfully'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class PodProductCatalogWizard(models.TransientModel):
    """Extended catalog model to link with wizard."""

    _inherit = 'pod.product.catalog'

    wizard_id = fields.Many2one(
        comodel_name='pod.catalog.wizard',
        string='Wizard',
        ondelete='cascade',
    )
