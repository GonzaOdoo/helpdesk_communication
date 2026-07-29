from odoo import fields, models, api
from markupsafe import Markup


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

    remote_stage_name = fields.Char(
        string="Estado en base sinc.",
        readonly=True,
        copy=False,
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
        service = self.env["helpdesk.bridge.service"]
        for ticket in self.filtered("bridge_link_id"):
            service.sync_ticket(ticket)
            if "stage_id" in vals:
                service.push_stage(ticket)
        return res


    def message_post(self, **kwargs):
        message = super().message_post(**kwargs)
    
        if self.env.context.get("bridge_sync"):
            return message
    
        if (
            self.bridge_link_id
            and message.message_type == "comment"
            and not message.subtype_id.internal
        ):
            self.env["helpdesk.bridge.service"].push_message(
                self,
                message,
            )
    
        return message

    @api.model
    def bridge_receive_message(self, payload):
        uuid = payload["uuid"]
        body = payload["body"]
    
        link = self.env["helpdesk.bridge.link"].search([
            ("uuid", "=", uuid),
        ], limit=1)
    
        if not link:
            return False
    
        ticket = link.local_ref
    
        ticket.with_context(
            bridge_sync=True,
        ).message_post(
            body=Markup(body),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
    
        return True

    @api.model
    def bridge_create_ticket(self, payload):
        vals = payload["vals"]
        uuid = payload["uuid"]
        bridge = self.env["helpdesk.bridge"].search([
            ("role", "=", "support"),
        ], limit=1)
    
        if not bridge:
            raise UserError("No support bridge configured.")
    
        ticket = self.with_context(
            bridge_sync=True,
        ).create(vals)
    
        link = self.env["helpdesk.bridge.link"].create({
            "bridge_id": bridge.id,
            "uuid": uuid,
            "local_ref": f"{ticket._name},{ticket.id}",
            "remote_model": "helpdesk.ticket",
            "remote_res_id": 0,      # luego hablamos de esto
            "state": "linked",
        })
    
        ticket.bridge_link_id = link
    
        return ticket.id

    @api.model
    def bridge_receive_stage(self, payload):
        link = self.env["helpdesk.bridge.link"].search(
            [("uuid", "=", payload["uuid"])],
            limit=1,
        )
    
        if not link:
            return False
    
        ticket = link.local_ref
    
        ticket.with_context(
            bridge_sync=True,
        ).write({
            "remote_stage_name": payload["stage_name"],
        })
    
        return True