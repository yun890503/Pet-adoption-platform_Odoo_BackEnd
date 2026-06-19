from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_warm_paws_adoption = fields.Boolean(string="暖心毛孩認養申請", default=False, index=True)
    warm_paws_animal_product_id = fields.Many2one(
        "product.template",
        string="認養毛孩",
        domain=[("is_adoptable_animal", "=", True)],
        index=True,
    )
    warm_paws_adoption_stage = fields.Selection(
        [
            ("application", "申請審核中"),
            ("approved", "申請已通過"),
            ("completed", "已完成認養"),
        ],
        string="前台認養階段",
        default="application",
        index=True,
    )
    warm_paws_applicant_phone = fields.Char(string="聯絡電話")
    warm_paws_applicant_city = fields.Char(string="居住縣市")
    warm_paws_pet_experience = fields.Text(string="飼養經驗")
    warm_paws_family_members = fields.Text(string="家庭成員")
    warm_paws_other_pets = fields.Char(string="其他寵物")
    warm_paws_completed_date = fields.Date(string="完成認養日期")

    def _warm_paws_line_event_name(self):
        self.ensure_one()
        if self.state == "cancel":
            return "cancelled"
        if self.warm_paws_adoption_stage == "completed":
            return "completed"
        if self.state == "sale" or self.warm_paws_adoption_stage == "approved":
            return "approved"
        return "reviewing"

    def _warm_paws_notify_adoption(self, event_name=None):
        service = self.env["warm.paws.line.service"].sudo()
        for order in self.filtered("is_warm_paws_adoption"):
            service.notify_adoption(order, event_name or order._warm_paws_line_event_name())

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.filtered("is_warm_paws_adoption")._warm_paws_notify_adoption("created")
        return orders

    def write(self, vals):
        tracked = "state" in vals or "warm_paws_adoption_stage" in vals
        before = {order.id: order._warm_paws_line_event_name() for order in self if order.is_warm_paws_adoption} if tracked else {}
        result = super().write(vals)
        if tracked:
            for order in self.filtered("is_warm_paws_adoption"):
                after = order._warm_paws_line_event_name()
                if before.get(order.id) != after:
                    order._warm_paws_notify_adoption(after)
        return result

    def _compute_warm_paws_stage_from_state(self):
        for order in self:
            if not order.is_warm_paws_adoption or order.warm_paws_adoption_stage == "completed":
                continue
            if order.state in ("draft", "sent"):
                order.warm_paws_adoption_stage = "application"
            elif order.state == "sale":
                order.warm_paws_adoption_stage = "approved"

    def action_confirm(self):
        result = super().action_confirm()
        self.filtered("is_warm_paws_adoption").write({"warm_paws_adoption_stage": "approved"})
        return result

    def action_warm_paws_complete_adoption(self):
        self.filtered("is_warm_paws_adoption").write(
            {
                "warm_paws_adoption_stage": "completed",
                "warm_paws_completed_date": fields.Date.context_today(self),
            }
        )
        for order in self.filtered(lambda item: item.is_warm_paws_adoption and item.warm_paws_animal_product_id):
            order.warm_paws_animal_product_id.animal_status = "adopted"
        return True

    def to_warm_paws_application_dict(self):
        self.ensure_one()
        self._compute_warm_paws_stage_from_state()
        animal = self.warm_paws_animal_product_id
        status = "reviewing"
        status_label = "審核中"
        if self.warm_paws_adoption_stage == "completed":
            status = "completed"
            status_label = "已完成認養"
        elif self.state == "sale" or self.warm_paws_adoption_stage == "approved":
            status = "approved"
            status_label = "已通過"
        elif self.state == "cancel":
            status = "cancelled"
            status_label = "已取消"

        return {
            "id": self.id,
            "name": self.name,
            "number": self.name,
            "status": status,
            "statusLabel": status_label,
            "saleState": self.state,
            "stage": self.warm_paws_adoption_stage,
            "date": fields.Date.to_string(self.date_order.date()) if self.date_order else "",
            "completedDate": fields.Date.to_string(self.warm_paws_completed_date) if self.warm_paws_completed_date else "",
            "animal": animal.to_warm_paws_frontend_dict() if animal else {},
            "phone": self.warm_paws_applicant_phone or "",
            "city": self.warm_paws_applicant_city or "",
            "experience": self.warm_paws_pet_experience or "",
            "family": self.warm_paws_family_members or "",
            "otherPets": self.warm_paws_other_pets or "",
        }
