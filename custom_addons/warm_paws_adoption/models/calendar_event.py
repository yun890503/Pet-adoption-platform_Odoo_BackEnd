from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    is_warm_paws_visit = fields.Boolean(string="暖心毛孩訪視預約", default=False, index=True)
    warm_paws_sale_order_id = fields.Many2one("sale.order", string="認養申請")
    warm_paws_animal_product_id = fields.Many2one("product.template", string="訪視毛孩")
    warm_paws_phone = fields.Char(string="聯絡電話")
    warm_paws_note = fields.Text(string="前台備註")
    warm_paws_visit_state = fields.Selection(
        [
            ("scheduled", "已預約"),
            ("cancelled", "已取消"),
        ],
        string="訪視狀態",
        default="scheduled",
        index=True,
    )

    def to_warm_paws_visit_dict(self):
        self.ensure_one()
        animal = self.warm_paws_animal_product_id
        return {
            "id": self.id,
            "name": self.name,
            "start": fields.Datetime.to_string(self.start) if self.start else "",
            "stop": fields.Datetime.to_string(self.stop) if self.stop else "",
            "phone": self.warm_paws_phone or "",
            "note": self.warm_paws_note or "",
            "state": self.warm_paws_visit_state or "scheduled",
            "isCancelled": self.warm_paws_visit_state == "cancelled",
            "saleOrderId": self.warm_paws_sale_order_id.id,
            "saleOrderName": self.warm_paws_sale_order_id.name or "",
            "animal": animal.to_warm_paws_frontend_dict() if animal else {},
        }
