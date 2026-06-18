from odoo import fields, models


class WarmPawsVolunteerApplication(models.Model):
    _name = "warm.paws.volunteer.application"
    _description = "Volunteer Application"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True)
    phone = fields.Char(required=True)
    email = fields.Char(required=True)
    available_time = fields.Char(string="Available Time")
    message = fields.Text()
    state = fields.Selection(
        [
            ("new", "新申請"),
            ("contacted", "已聯繫"),
            ("accepted", "已加入"),
            ("rejected", "未加入"),
        ],
        default="new",
        tracking=True,
    )
