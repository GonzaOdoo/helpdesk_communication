from odoo import api, fields, models


class HelpdeskBridgeField(models.Model):
    _name = "helpdesk.bridge.field"
    _description = "Helpdesk Bridge Field"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)

    active = fields.Boolean(default=True)

    bridge_id = fields.Many2one(
        "helpdesk.bridge",
        required=True,
        ondelete="cascade",
    )

    field_id = fields.Many2one(
        "ir.model.fields",
        required=True,
        ondelete="cascade",
        domain=[
            ("model", "=", "helpdesk.ticket"),
            ("store", "=", True),
            ("compute", "=", False),
        ],
    )

    field_name = fields.Char(
        related="field_id.name",
        store=True,
        readonly=True,
    )

    field_description = fields.Char(
        related="field_id.field_description",
        store=True,
        readonly=True,
    )

    ttype = fields.Selection(
        related="field_id.ttype",
        store=True,
        readonly=True,
    )

    direction = fields.Selection([
        ("ab", "Base A → Base B"),
        ("ba", "Base B → Base A"),
        ("both", "Ambos sentidos"),
    ], default="both", required=True)

    sync_mode = fields.Selection([
        ("copy", "Copiar"),
        ("mapping", "Mapear"),
    ], default="copy", required=True)

    mapping_ids = fields.One2many(
        "helpdesk.bridge.field.mapping",
        "bridge_field_id",
    )

    notes = fields.Text()

    is_mapping_supported = fields.Boolean(
        compute="_compute_is_mapping_supported"
    )

    @api.depends("ttype")
    def _compute_is_mapping_supported(self):
        supported = {
            "selection",
            "many2one",
            "char",
            "integer",
        }
    
        for rec in self:
            rec.is_mapping_supported = rec.ttype in supported
    _sql_constraints = [
        (
            "bridge_field_unique",
            "unique(bridge_id, field_id)",
            "This field is already configured for this bridge.",
        ),
    ]
class HelpdeskBridgeFieldMapping(models.Model):
    _name = "helpdesk.bridge.field.mapping"
    _description = "Helpdesk Bridge Field Mapping"
    _order = "id"

    bridge_field_id = fields.Many2one(
        "helpdesk.bridge.field",
        required=True,
        ondelete="cascade",
    )

    local_key = fields.Char(
        required=True,
        help="Value stored in Base A",
    )

    remote_key = fields.Char(
        required=True,
        help="Value stored in Base B",
    )

    description = fields.Char()

    _sql_constraints = [
        (
            "bridge_mapping_unique",
            "unique(bridge_field_id, local_key)",
            "This local value is already mapped.",
        ),
    ]