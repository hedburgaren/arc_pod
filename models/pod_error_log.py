# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api


class PodErrorLog(models.Model):
    """Model to store API error logs for POD providers."""

    _name = 'pod.error.log'
    _description = 'POD Error Log'
    _order = 'timestamp desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
    )
    provider_id = fields.Many2one(
        comodel_name='pod.provider',
        string='Provider',
        required=True,
        ondelete='cascade',
    )
    error_message = fields.Text(
        string='Error Message',
        required=True,
    )
    error_code = fields.Char(
        string='Error Code',
        help='HTTP status code',
    )
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True,
    )
    request_endpoint = fields.Char(
        string='Request Endpoint',
    )

    @api.depends('timestamp', 'provider_id')
    def _compute_name(self):
        """Compute name from timestamp and provider."""
        for record in self:
            if record.timestamp and record.provider_id:
                timestamp_str = fields.Datetime.to_string(record.timestamp)
                record.name = f"{timestamp_str} - {record.provider_id.name}"
            else:
                record.name = 'Error Log'
