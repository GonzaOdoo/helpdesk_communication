from uuid import uuid4

from odoo import fields, models


class HelpdeskBridgeLink(models.Model):
    _name = "helpdesk.bridge.link"
    _description = "Bridge Link"
    _rec_name = "uuid"

    active = fields.Boolean(default=True)

    uuid = fields.Char(
        default=lambda self: str(uuid4()),
        required=True,
        copy=False,
        index=True,
    )

    bridge_id = fields.Many2one(
        "helpdesk.bridge",
        required=True,
        ondelete="cascade",
    )

    local_ref = fields.Reference(
        selection=[
            ('helpdesk.ticket', 'Ticket'),
        ],
        required=True,
    )
    remote_model = fields.Char(required=True)

    remote_res_id = fields.Integer()

    state = fields.Selection([
        ("draft", "Draft"),
        ("linked", "Linked"),
        ("error", "Error"),
    ], default="draft")

    last_sync = fields.Datetime(readonly=True)