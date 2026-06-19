from odoo import fields, models


class WarmPawsVolunteerTestimonial(models.Model):
    _name = "warm.paws.volunteer.testimonial"
    _description = "Warm Paws Volunteer Testimonial"
    _order = "create_date desc, id desc"

    partner_id = fields.Many2one("res.partner", string="會員", ondelete="set null", index=True)
    name = fields.Char(string="姓名", required=True)
    role = fields.Char(string="志工類型", default="暖心志工")
    rating = fields.Integer(string="評分", default=5)
    message = fields.Text(string="心得", required=True)
    is_published = fields.Boolean(string="前台顯示", default=True, index=True)

    def to_warm_paws_frontend_dict(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name or "",
            "role": self.role or "暖心志工",
            "rating": max(1, min(5, self.rating or 5)),
            "message": self.message or "",
            "createdAt": fields.Datetime.to_string(self.create_date),
            "partnerId": self.partner_id.id,
        }
