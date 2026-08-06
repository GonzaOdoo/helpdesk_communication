from odoo import fields, models


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    bridge_id = fields.Many2one(
        "helpdesk.bridge",
        string="Bridge",
    )

class HelpdeskTag(models.Model):
    _inherit = "helpdesk.tag"

    bridge_remote_team_id = fields.Integer(
        string="Remote Team ID",
        help="ID del equipo en la base remota donde se creará el ticket."
    )
    bridge_enabled = fields.Boolean(
        string="Sincronizar con otra base",
        help="Los tickets con esta etiqueta se enviarán a la base remota.",
    )
