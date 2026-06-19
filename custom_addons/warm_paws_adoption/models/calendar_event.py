from odoo import api, fields, models


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

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        service = self.env["warm.paws.line.service"].sudo()
        for event in events.filtered(lambda item: item.is_warm_paws_visit and item.warm_paws_visit_state != "cancelled"):
            service.notify_visit(event, "created")
        return events

    def write(self, vals):
        tracked = "warm_paws_visit_state" in vals
        before = {event.id: event.warm_paws_visit_state for event in self if event.is_warm_paws_visit} if tracked else {}
        result = super().write(vals)
        if tracked:
            service = self.env["warm.paws.line.service"].sudo()
            for event in self.filtered("is_warm_paws_visit"):
                if before.get(event.id) != event.warm_paws_visit_state:
                    service.notify_visit(event, "cancelled" if event.warm_paws_visit_state == "cancelled" else "created")
        return result

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
