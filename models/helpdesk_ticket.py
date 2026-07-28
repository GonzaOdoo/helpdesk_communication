from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    bridge_link_id = fields.Many2one(
        "helpdesk.bridge.link",
        copy=False,
        readonly=True,
    )

    bridge_uuid = fields.Char(
        related="bridge_link_id.uuid",
        store=True,
        readonly=True,
    )

    is_bridge_ticket = fields.Boolean(
        compute="_compute_is_bridge_ticket",
    )

    def _compute_is_bridge_ticket(self):
        for ticket in self:
            ticket.is_bridge_ticket = bool(ticket.bridge_link_id)

    def action_create_remote_ticket(self):
        self.ensure_one()
    
        self.env["helpdesk.bridge.service"].create_remote_ticket(self)

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("bridge_sync"):
            return res
        for ticket in self:
            if ticket.bridge_link_id:
                self.env["helpdesk.bridge.service"].sync_ticket(ticket)
        return res

    def message_post(self, **kwargs):
        message = super().message_post(**kwargs)

        if self.env.context.get("bridge_sync"):
            return message

        if not self.bridge_link_id:
            return message

        # Solo comentarios normales
        if (
            message.message_type == "comment"
            and not message.subtype_id.internal
        ):
            self.env["helpdesk.bridge.service"].sync_message(
                self,
                message,
            )

        return message