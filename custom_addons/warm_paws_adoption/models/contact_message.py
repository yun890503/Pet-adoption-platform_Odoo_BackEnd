from odoo import fields, models


class WarmPawsContactMessage(models.Model):
    _name = "warm.paws.contact.message"
    _description = "Contact Message"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True)
    email = fields.Char(required=True)
    phone = fields.Char()
    message = fields.Text(required=True)
    state = fields.Selection(
        [
            ("new", "新訊息"),
            ("replied", "已回覆"),
            ("closed", "已結案"),
        ],
        default="new",
        tracking=True,
    )
