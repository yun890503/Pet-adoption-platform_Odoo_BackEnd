import json
from datetime import datetime, timedelta

import odoo
from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request


def cors_response(payload=None, status=200):
    body = json.dumps(payload or {}, ensure_ascii=False)
    return request.make_response(
        body,
        headers=[
            ("Content-Type", "application/json; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
        ],
        status=status,
    )


def json_body():
    raw = request.httprequest.get_data(as_text=True)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def bearer_token():
    header = request.httprequest.headers.get("Authorization") or ""
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return ""


def current_partner():
    token = bearer_token()
    if not token:
        return request.env["res.partner"]
    return request.env["res.partner"].sudo().search([("warm_paws_api_token", "=", token)], limit=1)


def current_db():
    return request.db or "Pet-adoption-platform"


def is_preflight():
    return request.httprequest.method == "OPTIONS"


def parse_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def sale_order_domain_for_partner(partner):
    return [("is_warm_paws_adoption", "=", True), ("partner_id", "=", partner.id)]


def parse_visit_datetime(date_value, time_value):
    date_text = (date_value or "").strip()
    time_text = (time_value or "").strip()
    if not date_text or not time_text:
        return None
    try:
        return datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


class WarmPawsApi(http.Controller):
    @http.route("/warm_paws/api/<path:any_path>", type="http", auth="public", methods=["OPTIONS"], csrf=False)
    def options(self, any_path=None, **kwargs):
        return cors_response({"ok": True})

    @http.route("/warm_paws/api/animals", type="http", auth="public", methods=["GET"], csrf=False)
    def animals(self, **kwargs):
        domain = [("active", "=", True), ("is_adoptable_animal", "=", True)]
        animal_type = kwargs.get("type")
        name = kwargs.get("name")
        breed = kwargs.get("breed")
        search = kwargs.get("search")
        limit = int(kwargs.get("limit") or 0)
        sort = kwargs.get("sort") or "newest"

        if animal_type in ("dog", "cat"):
            domain.append(("animal_type", "=", animal_type))
        if name:
            domain.append(("name", "ilike", name))
        if breed:
            domain.append(("animal_breed", "ilike", breed))
        if search:
            domain += ["|", ("name", "ilike", search), ("animal_breed", "ilike", search)]

        order = "create_date desc"
        if sort == "age":
            order = "animal_age_value asc"
        elif sort == "breed":
            order = "animal_breed asc"

        records = request.env["product.template"].sudo().search(domain, order=order, limit=limit)
        return cors_response([record.to_warm_paws_frontend_dict() for record in records])

    @http.route("/warm_paws/api/animals/<int:animal_id>", type="http", auth="public", methods=["GET"], csrf=False)
    def animal_detail(self, animal_id, **kwargs):
        animal = request.env["product.template"].sudo().browse(animal_id).exists()
        if animal and not animal.is_adoptable_animal:
            animal = False
        if not animal:
            return cors_response({"message": "Animal not found."}, status=404)
        return cors_response(animal.to_warm_paws_frontend_dict())

    @http.route("/warm_paws/api/adoption-inquiries", type="http", auth="public", methods=["POST", "OPTIONS"], csrf=False)
    def adoption_inquiry(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        if bearer_token():
            return self.adoption_application()

        data = json_body()
        animal = request.env["product.template"].sudo().browse(int(data.get("animalId") or 0)).exists()
        if animal and not animal.is_adoptable_animal:
            animal = False
        if not animal:
            return cors_response({"message": "Animal not found."}, status=404)

        inquiry = request.env["warm.paws.adoption.inquiry"].sudo().create(
            {
                "animal_product_id": animal.id,
                "name": data.get("name") or "",
                "phone": data.get("phone") or "",
                "email": data.get("email") or "",
                "city": data.get("city") or "",
                "experience": data.get("experience") or "",
                "family_members": data.get("family") or data.get("familyMembers") or "",
                "other_pets": data.get("otherPets") or "",
                "message": data.get("message") or "",
            }
        )
        return cors_response({"id": inquiry.id, "message": "Adoption inquiry created."}, status=201)

    @http.route("/warm_paws/api/adoption-applications", type="http", auth="public", methods=["POST", "OPTIONS"], csrf=False)
    def adoption_application(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        partner = current_partner()
        if not partner:
            return cors_response({"message": "Unauthorized."}, status=401)

        data = json_body()
        animal = request.env["product.template"].sudo().browse(parse_int(data.get("animalId"))).exists()
        if animal and not animal.is_adoptable_animal:
            animal = False
        if not animal:
            return cors_response({"message": "Animal not found."}, status=404)

        product = animal.product_variant_id
        if not product:
            return cors_response({"message": "Animal product variant not found."}, status=404)

        values = {
            "partner_id": partner.id,
            "is_warm_paws_adoption": True,
            "warm_paws_animal_product_id": animal.id,
            "warm_paws_adoption_stage": "application",
            "warm_paws_applicant_phone": data.get("phone") or partner.phone or partner.mobile or "",
            "warm_paws_applicant_city": data.get("city") or partner.city or "",
            "warm_paws_pet_experience": data.get("experience") or "",
            "warm_paws_family_members": data.get("family") or data.get("familyMembers") or "",
            "warm_paws_other_pets": data.get("otherPets") or "",
            "client_order_ref": f"Warm Paws Adoption - {animal.name}",
            "note": data.get("message") or "",
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": f"認養申請：{animal.name}",
                        "product_uom_qty": 1,
                        "price_unit": product.lst_price,
                    },
                )
            ],
        }
        order = request.env["sale.order"].sudo().create(values)
        return cors_response(order.to_warm_paws_application_dict(), status=201)

    @http.route("/warm_paws/api/me/adoption-applications", type="http", auth="public", methods=["GET", "OPTIONS"], csrf=False)
    def my_adoption_applications(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        partner = current_partner()
        if not partner:
            return cors_response({"message": "Unauthorized."}, status=401)

        orders = request.env["sale.order"].sudo().search(sale_order_domain_for_partner(partner), order="date_order desc, id desc")
        return cors_response([order.to_warm_paws_application_dict() for order in orders])

    @http.route("/warm_paws/api/me/adoption-records", type="http", auth="public", methods=["GET", "OPTIONS"], csrf=False)
    def my_adoption_records(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        partner = current_partner()
        if not partner:
            return cors_response({"message": "Unauthorized."}, status=401)

        domain = sale_order_domain_for_partner(partner) + [("warm_paws_adoption_stage", "=", "completed")]
        orders = request.env["sale.order"].sudo().search(domain, order="warm_paws_completed_date desc, date_order desc")
        return cors_response([order.to_warm_paws_application_dict() for order in orders])

    @http.route("/warm_paws/api/visit-appointments", type="http", auth="public", methods=["POST", "OPTIONS"], csrf=False)
    def visit_appointment(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        partner = current_partner()
        if not partner:
            return cors_response({"message": "Unauthorized."}, status=401)

        data = json_body()
        animal = request.env["product.template"].sudo().browse(parse_int(data.get("animalId"))).exists()
        if animal and not animal.is_adoptable_animal:
            animal = False
        if not animal:
            return cors_response({"message": "Animal not found."}, status=404)

        sale_order = request.env["sale.order"].sudo().browse(parse_int(data.get("saleOrderId"))).exists()
        if sale_order and (sale_order.partner_id != partner or not sale_order.is_warm_paws_adoption):
            sale_order = False

        start = parse_visit_datetime(data.get("date"), data.get("time"))
        if not start:
            return cors_response({"message": "Visit date and time are required."}, status=400)

        existing_future_visit = (
            request.env["calendar.event"]
            .sudo()
            .search(
                [
                    ("is_warm_paws_visit", "=", True),
                    ("warm_paws_visit_state", "!=", "cancelled"),
                    ("partner_ids", "in", partner.id),
                    ("start", ">=", datetime.now()),
                ],
                limit=1,
            )
        )
        if existing_future_visit:
            return cors_response(
                {
                    "message": "You already have an upcoming visit appointment. Please cancel it before booking another date."
                },
                status=409,
            )

        existing_same_animal_visit = (
            request.env["calendar.event"]
            .sudo()
            .search(
                [
                    ("is_warm_paws_visit", "=", True),
                    ("warm_paws_visit_state", "!=", "cancelled"),
                    ("partner_ids", "in", partner.id),
                    ("warm_paws_animal_product_id", "=", animal.id),
                    ("start", ">=", datetime.now()),
                ],
                limit=1,
            )
        )
        if existing_same_animal_visit:
            return cors_response(
                {"message": "This animal already has an upcoming visit appointment for your account."},
                status=409,
            )

        stop = start + timedelta(hours=1)
        event = request.env["calendar.event"].sudo().create(
            {
                "name": f"認養訪視：{animal.name} - {partner.name}",
                "start": start,
                "stop": stop,
                "partner_ids": [(6, 0, [partner.id])],
                "description": data.get("note") or "",
                "is_warm_paws_visit": True,
                "warm_paws_sale_order_id": sale_order.id if sale_order else False,
                "warm_paws_animal_product_id": animal.id,
                "warm_paws_phone": data.get("phone") or partner.phone or partner.mobile or "",
                "warm_paws_note": data.get("note") or "",
                "warm_paws_visit_state": "scheduled",
            }
        )
        return cors_response(event.to_warm_paws_visit_dict(), status=201)

    @http.route("/warm_paws/api/visit-appointments/<int:event_id>/cancel", type="http", auth="public", methods=["POST", "OPTIONS"], csrf=False)
    def cancel_visit_appointment(self, event_id, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        partner = current_partner()
        if not partner:
            return cors_response({"message": "Unauthorized."}, status=401)

        event = request.env["calendar.event"].sudo().browse(event_id).exists()
        if not event or not event.is_warm_paws_visit or partner not in event.partner_ids:
            return cors_response({"message": "Visit appointment not found."}, status=404)

        event.write({"warm_paws_visit_state": "cancelled"})
        return cors_response(event.to_warm_paws_visit_dict())

    @http.route("/warm_paws/api/me/visit-appointments", type="http", auth="public", methods=["GET", "OPTIONS"], csrf=False)
    def my_visit_appointments(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        partner = current_partner()
        if not partner:
            return cors_response({"message": "Unauthorized."}, status=401)

        events = (
            request.env["calendar.event"]
            .sudo()
            .search([("is_warm_paws_visit", "=", True), ("partner_ids", "in", partner.id)], order="start desc")
        )
        return cors_response([event.to_warm_paws_visit_dict() for event in events])

    @http.route("/warm_paws/api/volunteer-applications", type="http", auth="public", methods=["POST", "OPTIONS"], csrf=False)
    def volunteer_application(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        data = json_body()
        application = request.env["warm.paws.volunteer.application"].sudo().create(
            {
                "name": data.get("name") or "",
                "phone": data.get("phone") or "",
                "email": data.get("email") or "",
                "available_time": data.get("availableTime") or "",
                "message": data.get("message") or "",
            }
        )
        return cors_response({"id": application.id, "message": "Volunteer application created."}, status=201)

    @http.route("/warm_paws/api/contact-messages", type="http", auth="public", methods=["POST", "OPTIONS"], csrf=False)
    def contact_message(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        data = json_body()
        message = request.env["warm.paws.contact.message"].sudo().create(
            {
                "name": data.get("name") or "",
                "email": data.get("email") or "",
                "phone": data.get("phone") or "",
                "message": data.get("message") or "",
            }
        )
        return cors_response({"id": message.id, "message": "Contact message created."}, status=201)

    @http.route("/warm_paws/api/register", type="http", auth="public", methods=["POST", "OPTIONS"], csrf=False)
    def register(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        data = json_body()
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        if not email or not password:
            return cors_response({"message": "Email and password are required."}, status=400)

        existing = request.env["res.users"].sudo().search([("login", "=", email)], limit=1)
        if existing:
            return cors_response({"message": "Email already exists."}, status=409)

        user = (
            request.env["res.users"]
            .sudo()
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": data.get("name") or email.split("@")[0],
                    "login": email,
                    "email": email,
                    "password": password,
                    "groups_id": [(6, 0, [])],
                }
            )
        )
        partner = user.partner_id.sudo()
        partner.write(
            {
                "phone": data.get("phone") or "",
                "city": data.get("city") or "",
            }
        )
        partner.warm_paws_refresh_token()
        return cors_response(partner.to_warm_paws_member_dict(include_token=True), status=201)

    @http.route("/warm_paws/api/login", type="http", auth="public", methods=["POST", "OPTIONS"], csrf=False)
    def login(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        data = json_body()
        login = (data.get("email") or data.get("login") or "").strip()
        password = data.get("password") or ""
        if not login or not password:
            return cors_response({"message": "Email and password are required."}, status=400)

        user_record = (
            request.env["res.users"]
            .sudo()
            .search(["|", ("login", "=", login), ("email", "=", login)], limit=1)
        )
        auth_login = user_record.login if user_record else login

        try:
            auth_info = request.session.authenticate(
                current_db(),
                {"login": auth_login, "password": password, "type": "password"},
            )
        except AccessDenied:
            return cors_response({"message": "Invalid email or password."}, status=401)

        user = request.env["res.users"].sudo().browse(auth_info["uid"]).exists()
        if not user:
            return cors_response({"message": "Invalid email or password."}, status=401)

        partner = user.partner_id.sudo()
        partner.warm_paws_refresh_token()
        payload = partner.to_warm_paws_member_dict(include_token=True)
        payload["userId"] = user.id
        payload["login"] = user.login
        return cors_response(payload)

    @http.route("/warm_paws/api/me", type="http", auth="public", methods=["GET", "PUT", "PATCH", "OPTIONS"], csrf=False)
    def me(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        partner = current_partner()
        if not partner:
            return cors_response({"message": "Unauthorized."}, status=401)

        if request.httprequest.method in ("PUT", "PATCH"):
            data = json_body()
            values = {}
            allowed = {
                "name": "name",
                "email": "email",
                "phone": "phone",
                "mobile": "mobile",
                "city": "city",
                "street": "street",
                "street2": "street2",
                "zip": "zip",
            }
            for key, field_name in allowed.items():
                if key in data:
                    values[field_name] = data.get(key) or ""
            if values:
                partner.sudo().write(values)

        return cors_response(partner.to_warm_paws_member_dict(include_token=True))

    @http.route("/warm_paws/api/me/favorites", type="http", auth="public", methods=["GET", "POST", "OPTIONS"], csrf=False)
    def my_favorites(self, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        partner = current_partner()
        if not partner:
            return cors_response({"message": "Unauthorized."}, status=401)

        if request.httprequest.method == "POST":
            data = json_body()
            animal = request.env["product.template"].sudo().browse(int(data.get("animalId") or 0)).exists()
            if animal and not animal.is_adoptable_animal:
                animal = False
            if not animal:
                return cors_response({"message": "Animal not found."}, status=404)

            if animal in partner.warm_paws_favorite_ids:
                partner.warm_paws_favorite_ids = [(3, animal.id)]
            else:
                partner.warm_paws_favorite_ids = [(4, animal.id)]

        return cors_response([animal.to_warm_paws_frontend_dict() for animal in partner.warm_paws_favorite_ids])

    @http.route("/warm_paws/api/members/<int:member_id>/favorites", type="http", auth="public", methods=["GET", "POST", "OPTIONS"], csrf=False)
    def member_favorites(self, member_id, **kwargs):
        if is_preflight():
            return cors_response({"ok": True})
        member = request.env["res.partner"].sudo().browse(member_id).exists()
        if not member:
            return cors_response({"message": "Member not found."}, status=404)

        if request.httprequest.method == "POST":
            data = json_body()
            animal = request.env["product.template"].sudo().browse(int(data.get("animalId") or 0)).exists()
            if animal and not animal.is_adoptable_animal:
                animal = False
            if not animal:
                return cors_response({"message": "Animal not found."}, status=404)
            if animal in member.warm_paws_favorite_ids:
                member.warm_paws_favorite_ids = [(3, animal.id)]
            else:
                member.warm_paws_favorite_ids = [(4, animal.id)]

        return cors_response([animal.to_warm_paws_frontend_dict() for animal in member.warm_paws_favorite_ids])
