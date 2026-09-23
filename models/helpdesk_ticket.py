from odoo import fields, models, api
from markupsafe import Markup
from odoo.exceptions import UserError
from lxml import html, etree
import logging

_logger = logging.getLogger(__name__)
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
    remote_ticket_ref = fields.Char(
        string="Referencia base sinc.",
        readonly=True,
        copy=False,
    )
    solicitante_ref = fields.Char("Solicitante")

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
        body = payload.get("body", "")
        attachments = payload.get("attachments", [])
    
        link = self.env["helpdesk.bridge.link"].search([
            ("uuid", "=", uuid),
        ], limit=1)
    
        if not link:
            return False
    
        ticket = link.local_ref
    
        attachment_mapping = {}
    
        # Crear los attachments en la base remota
        for attachment in attachments:
            remote_attachment = self.env["ir.attachment"].with_context(
                bridge_sync=True,
            ).create({
                "name": attachment["name"],
                "datas": attachment["datas"],
                "mimetype": attachment.get("mimetype"),
                "description": attachment.get("description"),
            })
    
            attachment_mapping[attachment["id"]] = remote_attachment
    
        # Reemplazar las referencias de las imágenes inline
        body = self._replace_attachment_references(
            body,
            attachment_mapping,
        )
    
        message = ticket.with_context(
            bridge_sync=True,
        ).message_post(
            body=Markup(body),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            attachment_ids=[
                attachment.id
                for attachment in attachment_mapping.values()
            ],
        )
    
        return message.id

    @api.model
    def bridge_create_ticket(self, payload):
        vals = payload["vals"]
        uuid = payload["uuid"]
    
        attachments = vals.pop("attachments", [])
    
        bridge = self.env["helpdesk.bridge"].search([
            ("role", "=", "support"),
        ], limit=1)
    
        if not bridge:
            raise UserError("No support bridge configured.")
    
        # Crear primero los attachments para obtener sus IDs remotos.
        attachment_mapping = {}
    
        for attachment in attachments:
            remote_attachment = self.env["ir.attachment"].with_context(
                bridge_sync=True,
            ).create({
                "name": attachment["name"],
                "datas": attachment["datas"],
                "mimetype": attachment.get("mimetype"),
                "description": attachment.get("description"),
                "res_model": "helpdesk.ticket",
                "res_id": 0,
            })
    
            attachment_mapping[attachment["id"]] = remote_attachment
            _logger.info(attachment_mapping)
        # Reemplazar referencias de los attachments en la descripción.
        vals["description"] = self._replace_attachment_references(
            vals.get("description"),
            attachment_mapping,
        )
        _logger.info("ANTES CREATE description: %s", vals.get("description"))

        ticket = self.with_context(
            bridge_sync=True,
        ).create(vals)
        
        _logger.info(
            "DESPUES CREATE description: %s",
            ticket.description,
        )
        # Asociar los attachments al ticket recién creado.
        for attachment in attachment_mapping.values():
            attachment.write({
                "res_id": ticket.id,
            })
    
        link = self.env["helpdesk.bridge.link"].create({
            "bridge_id": bridge.id,
            "uuid": uuid,
            "local_ref": f"{ticket._name},{ticket.id}",
            "remote_model": "helpdesk.ticket",
            "remote_res_id": 0,
            "state": "linked",
        })
    
        ticket.bridge_link_id = link
    
        return {
            "id": ticket.id,
            "ticket_ref": ticket.ticket_ref,
            "stage": ticket.stage_id.name,
        }

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


    @api.model
    def support_receive_message(self, payload):
        ticket_id = payload.get("ticket_id")
        body = payload.get("body")
    
        if not ticket_id:
            return False
    
        if not body:
            return False
    
        ticket = self.browse(ticket_id).exists()
    
        if not ticket:
            return False
    
        message = ticket.with_context(
            support_sync=True,
        ).message_post(
            body=Markup(body),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
    
        message.write({
            "support_sync": True,
        })
    
        return message.id



    def _replace_attachment_references(self, body, attachment_mapping):
        if not body or not attachment_mapping:
            return body
    
        try:
            root = html.fragment_fromstring(
                body,
                create_parent="div",
            )
    
            for element in root.xpath(".//*[@data-attachment-id]"):
                old_id = element.get("data-attachment-id")
    
                try:
                    old_id = int(old_id)
                except (TypeError, ValueError):
                    continue
    
                attachment = attachment_mapping.get(old_id)
    
                if not attachment:
                    continue
    
                new_id = attachment.id
    
                element.set(
                    "data-attachment-id",
                    str(new_id),
                )
    
                if element.tag == "img":
                    element.set(
                        "src",
                        f"/web/image/{new_id}",
                    )
    
            return "".join(
                etree.tostring(
                    child,
                    encoding="unicode",
                    method="html",
                )
                for child in root
            )
    
        except Exception:
            _logger.exception(
                "Could not replace attachment references in ticket description."
            )
            return body