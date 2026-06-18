import json

from odoo import api, fields, models


class WarmPawsAnimal(models.Model):
    _name = "warm.paws.animal"
    _description = "Adoptable Animal"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    type = fields.Selection(
        [("dog", "Dog"), ("cat", "Cat")],
        required=True,
        default="dog",
        tracking=True,
    )
    breed = fields.Char(required=True)
    age = fields.Char(required=True)
    age_value = fields.Float(help="Numeric age value for sorting.")
    gender = fields.Selection([("男生", "男生"), ("女生", "女生")], required=True)
    personality = fields.Text()
    health_status = fields.Text(string="Health Status")
    vaccine_info = fields.Text(string="Vaccine Info")
    neutered = fields.Selection(
        [("yes", "已結紮"), ("no", "尚未結紮"), ("unknown", "待評估")],
        default="unknown",
        tracking=True,
    )
    rescue_story = fields.Text(string="Rescue Story")
    weight = fields.Float(string="Weight (kg)")
    location = fields.Char(default="台中市")
    status = fields.Selection(
        [
            ("available", "開放認養中"),
            ("pending", "認養洽談中"),
            ("adopted", "已完成認養"),
        ],
        default="available",
        tracking=True,
    )
    images_json = fields.Text(
        string="Image URLs JSON",
        default="[]",
        help='JSON array, for example: ["https://example.com/a.jpg"].',
    )
    active = fields.Boolean(default=True)
    inquiry_count = fields.Integer(compute="_compute_inquiry_count")

    @api.depends("name")
    def _compute_inquiry_count(self):
        grouped = self.env["warm.paws.adoption.inquiry"].read_group(
            [("animal_id", "in", self.ids)],
            ["animal_id"],
            ["animal_id"],
        )
        counts = {item["animal_id"][0]: item["animal_id_count"] for item in grouped}
        for animal in self:
            animal.inquiry_count = counts.get(animal.id, 0)

    def get_image_urls(self):
        self.ensure_one()
        try:
            value = json.loads(self.images_json or "[]")
        except json.JSONDecodeError:
            value = []
        return value if isinstance(value, list) else []

    def to_frontend_dict(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "breed": self.breed,
            "age": self.age,
            "ageValue": self.age_value,
            "gender": self.gender,
            "personality": self.personality or "",
            "healthStatus": self.health_status or "",
            "vaccineInfo": self.vaccine_info or "",
            "neutered": dict(self._fields["neutered"].selection).get(self.neutered, self.neutered),
            "rescueStory": self.rescue_story or "",
            "weight": self.weight,
            "location": self.location or "",
            "status": self.status,
            "createdAt": fields.Datetime.to_string(self.create_date),
            "images": self.get_image_urls(),
        }
