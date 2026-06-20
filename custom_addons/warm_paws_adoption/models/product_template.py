import os

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_adoptable_animal = fields.Boolean(string="上架為認養毛孩", default=False, index=True)
    animal_type = fields.Selection([("dog", "狗狗"), ("cat", "貓咪")], string="毛孩類型")
    animal_breed = fields.Char(string="品種")
    animal_age = fields.Char(string="年齡")
    animal_age_value = fields.Float(string="年齡排序值")
    animal_gender = fields.Selection([("男生", "男生"), ("女生", "女生")], string="性別")
    animal_weight = fields.Float(string="體重（公斤）")
    animal_location = fields.Char(string="所在地", default="台中市")
    animal_status = fields.Selection(
        [
            ("available", "開放認養中"),
            ("pending", "認養洽談中"),
            ("adopted", "已完成認養"),
        ],
        string="認養狀態",
        default="available",
    )
    animal_neutered = fields.Selection(
        [("yes", "已結紮"), ("no", "尚未結紮"), ("unknown", "待評估")],
        string="結紮狀態",
        default="unknown",
    )
    animal_chip_status = fields.Selection(
        [("implanted", "已植入"), ("not_implanted", "尚未植入"), ("unknown", "待確認")],
        string="晶片",
        default="unknown",
    )

    animal_personality = fields.Text(string="個性")
    animal_health_status = fields.Text(string="健康狀況")
    animal_rescue_story = fields.Text(string="救援故事")
    animal_about = fields.Text(string="關於毛孩")

    animal_vaccine_info = fields.Text(string="疫苗資訊")
    animal_deworming_status = fields.Char(string="體內外驅蟲", default="已完成")
    animal_chip_implant_status = fields.Char(string="晶片植入", default="已完成")
    animal_health_record_status = fields.Char(string="健康紀錄狀況", default="良好")

    animal_traits = fields.Char(
        string="個性特質",
        help="請用逗號分隔，例如：活潑好動,親人撒嬌,喜歡玩耍",
    )
    animal_rating_human = fields.Integer(string="親人程度", default=5)
    animal_rating_active = fields.Integer(string="活潑程度", default=4)
    animal_rating_train = fields.Integer(string="容易訓練", default=4)
    animal_rating_cat = fields.Integer(string="對貓友善", default=3)
    animal_rating_dog = fields.Integer(string="對狗友善", default=4)
    animal_suitable_home = fields.Text(
        string="適合的家庭",
        help="每一行代表一個條件，前端會以清單顯示。",
    )
    animal_image_ids = fields.One2many(
        "warm.paws.product.animal.image",
        "product_tmpl_id",
        string="認養頁照片",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(values.get("is_adoptable_animal") for values in vals_list):
            self.env["warm.paws.cache"].sudo().clear_animals()
        return records

    def write(self, vals):
        was_adoptable = any(self.mapped("is_adoptable_animal"))
        result = super().write(vals)
        animal_fields = {
            "is_adoptable_animal",
            "active",
            "name",
            "image_1920",
            "animal_type",
            "animal_breed",
            "animal_age",
            "animal_age_value",
            "animal_gender",
            "animal_weight",
            "animal_location",
            "animal_status",
            "animal_neutered",
            "animal_chip_status",
            "animal_personality",
            "animal_health_status",
            "animal_rescue_story",
            "animal_about",
            "animal_vaccine_info",
            "animal_deworming_status",
            "animal_chip_implant_status",
            "animal_health_record_status",
            "animal_traits",
            "animal_rating_human",
            "animal_rating_active",
            "animal_rating_train",
            "animal_rating_cat",
            "animal_rating_dog",
            "animal_suitable_home",
        }
        if (was_adoptable or any(self.mapped("is_adoptable_animal"))) and animal_fields.intersection(vals):
            self.env["warm.paws.cache"].sudo().clear_animals()
        return result

    def unlink(self):
        should_clear = any(self.mapped("is_adoptable_animal"))
        result = super().unlink()
        if should_clear:
            self.env["warm.paws.cache"].sudo().clear_animals()
        return result

    def _selection_label(self, field_name, value):
        return dict(self._fields[field_name].selection).get(value, value or "")

    def _split_lines(self, value):
        return [line.strip() for line in (value or "").splitlines() if line.strip()]

    def _split_traits(self):
        return [item.strip() for item in (self.animal_traits or "").split(",") if item.strip()]

    def _warm_paws_backend_base_url(self):
        base_url = (
            os.environ.get("BACKEND_URL")
            or self.env["ir.config_parameter"].sudo().get_param("warm_paws.backend_url")
            or self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        ).rstrip("/")
        return base_url

    def _warm_paws_image_url(self, model_key, record_id, field_name="image_1920"):
        path = f"/warm_paws/api/images/{model_key}/{record_id}/{field_name}"
        return f"{self._warm_paws_backend_base_url()}{path}"

    def get_animal_image_urls(self, image_mode="full"):
        self.ensure_one()
        images = []
        if self.image_1920:
            images.append(self._warm_paws_image_url("product-template", self.id, "image_1024"))
        images.extend(
            self._warm_paws_image_url("animal-image", image.id, "image")
            for image in self.animal_image_ids
            if image.image
        )
        return images

    def get_animal_cover_image_url(self):
        self.ensure_one()
        images = self.get_animal_image_urls(image_mode="cover")
        if images:
            return images[0]
        return self._warm_paws_image_url("product-template", self.id, "image_512")

    def to_warm_paws_frontend_dict(self, image_mode="full"):
        self.ensure_one()
        if image_mode == "cover":
            images = [self.get_animal_cover_image_url()]
        else:
            images = self.get_animal_image_urls(image_mode=image_mode)
        return {
            "id": self.id,
            "name": self.name,
            "type": self.animal_type,
            "breed": self.animal_breed or "",
            "age": self.animal_age or "",
            "ageValue": self.animal_age_value,
            "gender": self.animal_gender or "",
            "weight": self.animal_weight,
            "location": self.animal_location or "",
            "status": self.animal_status,
            "statusLabel": self._selection_label("animal_status", self.animal_status),
            "neutered": self._selection_label("animal_neutered", self.animal_neutered),
            "chipStatus": self._selection_label("animal_chip_status", self.animal_chip_status),
            "personality": self.animal_personality or "",
            "healthStatus": self.animal_health_status or "",
            "rescueStory": self.animal_rescue_story or "",
            "about": self.animal_about or "",
            "vaccineInfo": self.animal_vaccine_info or "",
            "dewormingStatus": self.animal_deworming_status or "",
            "chipImplantStatus": self.animal_chip_implant_status or "",
            "healthRecordStatus": self.animal_health_record_status or "",
            "traitTags": self._split_traits(),
            "ratings": [
                {"label": "親人程度", "score": self.animal_rating_human},
                {"label": "活潑程度", "score": self.animal_rating_active},
                {"label": "容易訓練", "score": self.animal_rating_train},
                {"label": "對貓友善", "score": self.animal_rating_cat},
                {"label": "對狗友善", "score": self.animal_rating_dog},
            ],
            "suitableHomes": self._split_lines(self.animal_suitable_home),
            "createdAt": fields.Datetime.to_string(self.create_date),
            "images": images,
            "productId": self.id,
            "price": self.list_price,
        }
