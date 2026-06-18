from odoo import fields, models


class WarmPawsAdoptionInquiry(models.Model):
    _name = "warm.paws.adoption.inquiry"
    _description = "Adoption Inquiry"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    animal_product_id = fields.Many2one(
        "product.template",
        string="認養毛孩產品",
        required=True,
        ondelete="cascade",
        domain=[("is_adoptable_animal", "=", True)],
    )
    name = fields.Char(required=True)
    phone = fields.Char(required=True)
    email = fields.Char(required=True)
    city = fields.Char(string="居住縣市")
    experience = fields.Text(string="飼養經驗")
    family_members = fields.Text(string="家庭成員")
    other_pets = fields.Char(string="是否有其他寵物")
    message = fields.Text()
    state = fields.Selection(
        [
            ("new", "新申請"),
            ("contacted", "已聯繫"),
            ("interview", "訪談中"),
            ("approved", "通過"),
            ("rejected", "未通過"),
        ],
        default="new",
        tracking=True,
    )
