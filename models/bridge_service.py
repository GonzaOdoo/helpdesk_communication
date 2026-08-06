from odoo import models, api
from odoo.exceptions import UserError
from lxml import html, etree
from markupsafe import Markup
from uuid import uuid4
import logging

_logger = logging.getLogger(__name__)
class HelpdeskBridgeService(models.AbstractModel):
    _name = "helpdesk.bridge.service"

    def create_remote_ticket(self, ticket):
        ticket.ensure_one()

        if ticket.bridge_link_id:
            return ticket.bridge_link_id
        bridge_tag = self._get_bridge_tag(ticket)
        if not bridge_tag:
            return False
        remote_team_id = bridge_tag.bridge_remote_team_id
        if not remote_team_id:
            return False
        team = ticket.team_id
        uuid = str(uuid4())
        if not team.bridge_id:
            raise UserError("The team has no bridge configured.")

        bridge = team.bridge_id

        vals = {
            "name": ticket.name,
            "description": ticket.description,
            "team_id": remote_team_id,
            "remote_ticket_ref":ticket.ticket_ref,
        }
        payload = {
            "vals": vals,
            "uuid": uuid,
        }
        remote_id = bridge.execute(
            "helpdesk.ticket",
            "bridge_create_ticket",
            payload,
        )
        link = self.env["helpdesk.bridge.link"].create({
            "bridge_id": bridge.id,
            "uuid": uuid,
            "local_ref": f"{ticket._name},{ticket.id}",
            "remote_model": "helpdesk.ticket",
            "remote_res_id": remote_id["id"],
            "state": "linked",
        })
        ticket.bridge_link_id = link
        ticket.remote_ticket_ref = remote_id["ticket_ref"]
        ticket.remote_stage_name = remote_id["stage"]
        self.push_stage(ticket)


    def _prepare_sync_values(self, ticket):
        bridge = ticket.bridge_link_id.bridge_id
    
        vals = {}
    
        for rule in bridge.field_ids.filtered("active"):
    
            if rule.direction not in ("ab", "both"):
                continue
    
            field = rule.field_id
    
            value = ticket[field.name]
    
            if rule.sync_mode == "mapping":
                value = self._map_value(rule, value)
    
            else:
                value = self._convert_value(field, value)
    
            vals[field.name] = value
    
        return vals

    def _convert_value(self, field, value):
        if field.ttype == "html":
            return str(value or "")
    
        if field.ttype in (
            "char",
            "text",
            "selection",
            "boolean",
            "integer",
            "float",
            "date",
            "datetime",
        ):
            return value
    
        return False

    def _map_value(self, rule, value):
        mapping = rule.mapping_ids.filtered(
            lambda m: m.local_key == str(value)
        )[:1]
    
        if mapping:
            return mapping.remote_key
    
        return value

    
    def sync_ticket(self, ticket):
        bridge = ticket.bridge_link_id.bridge_id
    
        vals = self._prepare_sync_values(ticket)
    
        if not vals:
            return
    
        link = ticket.bridge_link_id

        bridge.execute(
            "helpdesk.ticket",
            "write",
            [link.remote_res_id],
            vals,
            context={
                "bridge_sync": True,
            },
        )

    def sync_message(self, ticket, message):

        link = ticket.bridge_link_id
        bridge = link.bridge_id
    
        body = Markup(self._prepare_message_body(message))
        _logger.info(body)
        bridge.execute(
            "helpdesk.ticket",
            "message_post",
            [link.remote_res_id],
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            context={
                "bridge_sync": True,
            },
        )

    def push_message(self, ticket, message):
        link = ticket.bridge_link_id
        bridge = link.bridge_id
    
        body = Markup(self._prepare_message_body(message))
    
        bridge.execute(
            "helpdesk.ticket",
            "bridge_receive_message",
            {
                "uuid": link.uuid,
                "body": body,
            },
        )

    def push_stage(self, ticket):
        link = ticket.bridge_link_id
        bridge = link.bridge_id
    
        bridge.execute(
            "helpdesk.ticket",
            "bridge_receive_stage",
            {
                "uuid": link.uuid,
                "stage_name": ticket.stage_id.display_name,
            },
        )

    def _prepare_message_body(self, message):
        body = str(message.body or "")
    
        if not body:
            return ""
    
        try:
            root = html.fragment_fromstring(
                body,
                create_parent="div",
            )
    
            # Eliminar enlaces internos de Odoo pero conservar su contenido.
            for link in root.xpath(".//a"):
                href = link.attrib.get("href", "")
                if href.startswith("/odoo/"):
                    link.drop_tag()
    
            # Eliminar atributos específicos de Odoo que ya no sirven.
            for element in root.iter():
                for attr in (
                    "data-oe-id",
                    "data-oe-model",
                    "data-oe-type",
                    "target",
                    "class",
                ):
                    element.attrib.pop(attr, None)
    
            return "".join(
                etree.tostring(
                    child,
                    encoding="unicode",
                    method="html",
                )
                for child in root
            )
    
        except Exception:
            # Ante cualquier HTML mal formado,
            # devolvemos el original.
            return body


    def _get_remote_team_id(self, ticket):
        tags = ticket.tag_ids.filtered("bridge_remote_team_id")
    
        if not tags:
            return False
    
        if len(tags) > 1:
            raise UserError(
                "El ticket tiene más de una etiqueta configurada para sincronización."
            )
    
        return tags.bridge_remote_team_id

    def _get_bridge_tag(self, ticket):
        tags = ticket.tag_ids.filtered("bridge_enabled")
    
        if not tags:
            return False
    
        if len(tags) > 1:
            raise UserError(
                "Solo puede existir una etiqueta de sincronización por ticket."
            )
    
        tag = tags[0]
    
        if not tag.bridge_remote_team_id:
            raise UserError(
                "La etiqueta de sincronización no tiene configurado un equipo remoto."
            )
    
        return tag