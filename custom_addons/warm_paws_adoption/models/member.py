from odoo import fields, models


class WarmPawsMember(models.Model):
    _name = "warm.paws.member"
    _description = "Warm Paws Member"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True)
    email = fields.Char(required=True, index=True)
    phone = fields.Char()
    city = fields.Char()
    password = fields.Char()
    favorite_ids = fields.Many2many(
        "product.template",
        string="Favorite Animals",
        domain=[("is_adoptable_animal", "=", True)],
    )

    _sql_constraints = [
        ("email_unique", "unique(email)", "Email already exists."),
    ]

    def to_frontend_dict(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone or "",
            "city": self.city or "",
            "favorites": self.favorite_ids.ids,
        }
