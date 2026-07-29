from odoo import api, fields, models
from odoo.exceptions import UserError
from markupsafe import Markup
import xmlrpc.client


class HelpdeskBridge(models.Model):
    _name = "helpdesk.bridge"
    _description = "Helpdesk Remote Bridge"
    _rec_name = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    url = fields.Char(
        required=True,
        help="Example: https://support.company.com",
    )

    database = fields.Char(required=True)
    username = fields.Char(required=True)
    password = fields.Char(required=True)
    timeout = fields.Integer(default=30)

    last_connection = fields.Datetime(readonly=True)

    state = fields.Selection([
        ("never", "Never Tested"),
        ("ok", "Connected"),
        ("error", "Error"),
    ], default="never", readonly=True)

    company_id = fields.Many2one(
        "res.company",
    )

    role = fields.Selection(
        [
            ("initiator", "Initiator"),
            ("support", "Support"),
        ],
        default="initiator",
        required=True,
        help=(
            "Initiator: creates and updates tickets in the remote system.\n"
            "Support: receives tickets and only replies through the chatter."
        ),
    )

    sync_fields = fields.Boolean(
        default=True,
        help="Synchronize configured ticket fields.",
    )

    sync_messages = fields.Boolean(
        default=True,
        help="Synchronize chatter messages.",
    )

    allow_remote_ticket_creation = fields.Boolean(
        default=False,
        help="Allow the remote system to create tickets in this database.",
    )

    allow_remote_field_updates = fields.Boolean(
        default=False,
        help="Allow the remote system to update ticket fields.",
    )

    allow_remote_messages = fields.Boolean(
        default=True,
        help="Allow the remote system to post chatter messages.",
    )

    field_ids = fields.One2many(
        "helpdesk.bridge.field",
        "bridge_id",
        string="Synchronization Rules",
    )

    def get_uid(self):
        self.ensure_one()

        common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common",
            allow_none=True,
        )

        uid = common.authenticate(
            self.database,
            self.username,
            self.password,
            {},
        )

        if not uid:
            raise UserError("Authentication failed.")

        return uid

    def get_models(self):
        self.ensure_one()

        return xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object",
            allow_none=True,
        )

    def execute(self, model, method, *args, **kwargs):
        self.ensure_one()

        uid = self.get_uid()

        models_rpc = self.get_models()
        args = [self._rpc_serialize(arg) for arg in args]
        kwargs = self._rpc_serialize(kwargs)
        return models_rpc.execute_kw(
            self.database,
            uid,
            self.password,
            model,
            method,
            list(args),
            kwargs,
        )

    def _serialize(self, value):
        if isinstance(value, Markup):
            return str(value)
    
        return value
    def _serialize_dict(self, vals):
        return {
            key: self._serialize(value)
            for key, value in vals.items()
        }

    def _rpc_serialize(self, value):
        if isinstance(value, Markup):
            return str(value)
    
        if isinstance(value, dict):
            return {
                k: self._rpc_serialize(v)
                for k, v in value.items()
            }
    
        if isinstance(value, (list, tuple)):
            return [self._rpc_serialize(v) for v in value]
    
        return value

    def _prepare_sync_values(self, ticket):
        result = {}

        for field in bridge.sync_field_ids:
            if field.ttype in (
                "char",
                "text",
                "html",
                "boolean",
                "integer",
                "float",
                "date",
                "datetime",
                "selection",
            ):
                result[field.name] = ticket[field.name]


    def can_push_fields(self):
        self.ensure_one()
        return self.sync_fields and self.role == "initiator"
    
    
    def can_push_messages(self):
        self.ensure_one()
        return self.sync_messages
    
    
    def can_receive_fields(self):
        self.ensure_one()
        return self.allow_remote_field_updates
    
    
    def can_receive_messages(self):
        self.ensure_one()
        return self.allow_remote_messages
    
    
    def can_receive_ticket_creation(self):
        self.ensure_one()
        return self.allow_remote_ticket_creation