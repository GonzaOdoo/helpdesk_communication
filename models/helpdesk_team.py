from odoo import fields, models


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    bridge_id = fields.Many2one(
        "helpdesk.bridge",
        string="Bridge",
    )