from odoo import api, fields, models


class WarmPawsProductAnimalImage(models.Model):
    _name = "warm.paws.product.animal.image"
    _description = "Warm Paws Product Animal Image"
    _order = "sequence, id"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="毛孩產品",
        required=True,
        ondelete="cascade",
        domain=[("is_adoptable_animal", "=", True)],
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(default="認養頁照片")
    image = fields.Image(string="照片", required=True, max_width=1920, max_height=1920)
    mimetype = fields.Char(default="image/png")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["warm.paws.cache"].sudo().clear_animals()
        return records

    def write(self, vals):
        result = super().write(vals)
        if {"product_tmpl_id", "sequence", "name", "image", "mimetype"}.intersection(vals):
            self.env["warm.paws.cache"].sudo().clear_animals()
        return result

    def unlink(self):
        result = super().unlink()
        self.env["warm.paws.cache"].sudo().clear_animals()
        return result

    def to_data_url(self):
        self.ensure_one()
        if not self.image:
            return ""
        return f"data:{self.mimetype or 'image/png'};base64,{self.image.decode() if isinstance(self.image, bytes) else self.image}"
