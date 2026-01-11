# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from odoo import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PODOrderTransformer:
    """Helper class for converting Odoo orders to POD format."""

    def __init__(self, env):
        """
        Initialize the transformer.
        
        Args:
            env: Odoo environment
        """
        self.env = env

    def transform_for_printify(self, sale_order):
        """
        Transform sale order to Printify format.
        
        Args:
            sale_order: sale.order record
            
        Returns:
            dict: Order data ready for Printify API
            
        Raises:
            ValidationError: If required data is missing
        """
        self._validate_order(sale_order)
        
        # Extract line items with POD mappings
        line_items = []
        for line in sale_order.order_line:
            if line.product_id and line.product_id.pod_mapping_ids:
                for mapping in line.product_id.pod_mapping_ids:
                    if mapping.provider_id.code == 'printify':
                        line_items.append({
                            'product_id': mapping.pod_product_id.external_id if mapping.pod_product_id else '',
                            'variant_id': mapping.pod_variant_id.external_id if mapping.pod_variant_id else '',
                            'quantity': int(line.product_uom_qty),
                        })
        
        if not line_items:
            raise ValidationError(_("No Printify mappings found in order lines"))
        
        # Format address
        partner = sale_order.partner_shipping_id or sale_order.partner_id
        
        # Split name into first and last name
        name_parts = partner.name.split(' ', 1) if partner.name else ['', '']
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        order_data = {
            'external_id': sale_order.name,
            'line_items': line_items,
            'shipping_method': 1,  # Default shipping method
            'address_to': {
                'first_name': first_name,
                'last_name': last_name,
                'email': partner.email or '',
                'address1': partner.street or '',
                'address2': partner.street2 or '',
                'city': partner.city or '',
                'state_code': partner.state_id.code if partner.state_id else '',
                'zip': partner.zip or '',
                'country': partner.country_id.code if partner.country_id else '',
            }
        }
        
        _logger.info("Transformed order %s for Printify", sale_order.name)
        return order_data

    def transform_for_gelato(self, sale_order):
        """
        Transform sale order to Gelato format.
        
        Args:
            sale_order: sale.order record
            
        Returns:
            dict: Order data ready for Gelato API
            
        Raises:
            ValidationError: If required data is missing
        """
        self._validate_order(sale_order)
        
        # Extract line items with POD mappings
        line_items = []
        for line in sale_order.order_line:
            if line.product_id and line.product_id.pod_mapping_ids:
                for mapping in line.product_id.pod_mapping_ids:
                    if mapping.provider_id.code == 'gelato':
                        line_items.append({
                            'product_uid': mapping.pod_product_id.external_id if mapping.pod_product_id else '',
                            'variant_uid': mapping.pod_variant_id.external_id if mapping.pod_variant_id else '',
                            'quantity': int(line.product_uom_qty),
                        })
        
        if not line_items:
            raise ValidationError(_("No Gelato mappings found in order lines"))
        
        # Format address
        partner = sale_order.partner_shipping_id or sale_order.partner_id
        
        order_data = {
            'orderReferenceId': sale_order.name,
            'orderType': 'order',
            'customerEmail': partner.email or '',
            'items': line_items,
            'shippingAddress': {
                'firstName': partner.name or '',
                'lastName': '',
                'addressLine1': partner.street or '',
                'addressLine2': partner.street2 or '',
                'city': partner.city or '',
                'postCode': partner.zip or '',
                'country': partner.country_id.code if partner.country_id else '',
                'email': partner.email or '',
            }
        }
        
        _logger.info("Transformed order %s for Gelato", sale_order.name)
        return order_data

    def transform_for_printful(self, sale_order):
        """
        Transform sale order to Printful format.
        
        Args:
            sale_order: sale.order record
            
        Returns:
            dict: Order data ready for Printful API
            
        Raises:
            ValidationError: If required data is missing
        """
        self._validate_order(sale_order)
        
        # Extract line items with POD mappings
        line_items = []
        for line in sale_order.order_line:
            if line.product_id and line.product_id.pod_mapping_ids:
                for mapping in line.product_id.pod_mapping_ids:
                    if mapping.provider_id.code == 'printful':
                        line_items.append({
                            'sync_variant_id': mapping.pod_variant_id.external_id if mapping.pod_variant_id else '',
                            'quantity': int(line.product_uom_qty),
                        })
        
        if not line_items:
            raise ValidationError(_("No Printful mappings found in order lines"))
        
        # Format address
        partner = sale_order.partner_shipping_id or sale_order.partner_id
        
        order_data = {
            'external_id': sale_order.name,
            'recipient': {
                'name': partner.name or '',
                'address1': partner.street or '',
                'address2': partner.street2 or '',
                'city': partner.city or '',
                'state_code': partner.state_id.code if partner.state_id else '',
                'country_code': partner.country_id.code if partner.country_id else '',
                'zip': partner.zip or '',
                'email': partner.email or '',
            },
            'items': line_items,
        }
        
        _logger.info("Transformed order %s for Printful", sale_order.name)
        return order_data

    def _validate_order(self, sale_order):
        """
        Validate order has required data.
        
        Args:
            sale_order: sale.order record
            
        Raises:
            ValidationError: If required data is missing
        """
        if not sale_order:
            raise ValidationError(_("Sale order is required"))
        
        if not sale_order.order_line:
            raise ValidationError(_("Sale order has no lines"))
        
        # Check shipping address
        partner = sale_order.partner_shipping_id or sale_order.partner_id
        if not partner:
            raise ValidationError(_("Shipping address is required"))
        
        if not partner.street:
            raise ValidationError(_("Shipping address street is required"))
        
        if not partner.city:
            raise ValidationError(_("Shipping address city is required"))
        
        if not partner.country_id:
            raise ValidationError(_("Shipping address country is required"))
        
        if not partner.email:
            raise ValidationError(_("Customer email is required"))
        
        _logger.info("Order %s validated successfully", sale_order.name)
