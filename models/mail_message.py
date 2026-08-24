from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    support_sync = fields.Boolean(
        string="Mensaje de sincronización de soporte",
        default=False,
        index=True,
        copy=False,
    )