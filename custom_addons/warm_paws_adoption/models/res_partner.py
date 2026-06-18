from odoo import fields, models
import secrets


class ResPartner(models.Model):
    _inherit = "res.partner"

    warm_paws_api_token = fields.Char(copy=False, index=True)
    warm_paws_favorite_ids = fields.Many2many(
        "product.template",
        "warm_paws_partner_product_favorite_rel",
        "partner_id",
        "product_tmpl_id",
        string="暖心毛孩收藏",
        domain=[("is_adoptable_animal", "=", True)],
    )

    def warm_paws_refresh_token(self):
        self.ensure_one()
        self.warm_paws_api_token = secrets.token_urlsafe(32)
        return self.warm_paws_api_token

    def to_warm_paws_member_dict(self, include_token=False):
        self.ensure_one()
        payload = {
            "id": self.id,
            "partnerId": self.id,
            "name": self.name or "",
            "email": self.email or "",
            "phone": self.phone or "",
            "mobile": self.mobile or "",
            "city": self.city or "",
            "street": self.street or "",
            "street2": self.street2 or "",
            "zip": self.zip or "",
            "address": self.contact_address or "",
            "favorites": self.warm_paws_favorite_ids.ids,
        }
        if include_token:
            payload["token"] = self.warm_paws_api_token
        return payload
