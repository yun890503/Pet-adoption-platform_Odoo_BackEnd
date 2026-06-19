import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from odoo import fields, models

_logger = logging.getLogger(__name__)


class WarmPawsLineService(models.AbstractModel):
    _name = "warm.paws.line.service"
    _description = "Warm Paws LINE Service"

    def _param(self, key, fallback=""):
        env_key = f"WARM_PAWS_{key}".upper()
        env_value = os.environ.get(env_key)
        if env_value:
            return env_value
        return self.env["ir.config_parameter"].sudo().get_param(f"warm_paws.{key}", fallback) or fallback

    def verify_id_token(self, id_token):
        channel_id = self._param("line_channel_id", "2010432240")
        if not id_token or not channel_id:
            return {}

        data = urllib.parse.urlencode({"id_token": id_token, "client_id": channel_id}).encode("utf-8")
        request = urllib.request.Request(
            "https://api.line.me/oauth2/v2.1/verify",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as error:
            _logger.warning("LINE ID token verify failed: %s", error)
            return {}

    def push_flex(self, partner, alt_text, bubble):
        partner = partner.sudo()
        access_token = self._param("line_channel_access_token") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
        if not access_token or not partner.warm_paws_line_user_id or not partner.warm_paws_line_notify:
            return False

        payload = {
            "to": partner.warm_paws_line_user_id,
            "messages": [{"type": "flex", "altText": alt_text, "contents": bubble}],
        }
        request = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                response.read()
            return True
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            _logger.warning("LINE push failed for partner %s: %s %s", partner.id, error, details)
            return False
        except (urllib.error.URLError, TimeoutError) as error:
            _logger.warning("LINE push failed for partner %s: %s", partner.id, error)
            return False

    def _frontend_url(self, path):
        base = self._param("frontend_url", os.environ.get("FRONTEND_URL", "https://adoption-platform.zeabur.app")).rstrip("/")
        return f"{base}{path}"

    def _plain_datetime(self, value):
        if not value:
            return "-"
        try:
            dt_value = fields.Datetime.context_timestamp(self, value)
            return dt_value.strftime("%Y/%m/%d %H:%M")
        except Exception:
            return str(value)

    def _status_color(self, event_name):
        if event_name == "cancelled":
            return "#9ca3af"
        if event_name in ("approved", "completed"):
            return "#2f8f67"
        return "#ff8a3d"

    def _status_tint(self, event_name):
        if event_name == "cancelled":
            return "#f1f2f4"
        if event_name in ("approved", "completed"):
            return "#eef8f2"
        return "#fff4e8"

    def _adoption_stage_label(self, event_name):
        return {
            "created": "審核中",
            "reviewing": "審核中",
            "approved": "已通過",
            "completed": "已完成認養",
            "cancelled": "已取消",
        }.get(event_name, "審核中")

    def _visit_stage_label(self, event_name):
        return "預約已取消" if event_name == "cancelled" else "預約成功"

    def _info_row(self, label, value):
        return {
            "type": "box",
            "layout": "baseline",
            "spacing": "md",
            "paddingTop": "6px",
            "paddingBottom": "6px",
            "contents": [
                {"type": "text", "text": label, "color": "#7b5439", "size": "sm", "flex": 2},
                {
                    "type": "text",
                    "text": str(value or "-"),
                    "color": "#24211f",
                    "size": "sm",
                    "wrap": True,
                    "flex": 5,
                },
            ],
        }

    def _warm_card(self, title, subtitle, status, rows, action_label, action_path, header_color, footer_color, event_name):
        status_color = self._status_color(event_name)
        status_tint = self._status_tint(event_name)
        row_contents = []
        for index, row in enumerate(rows):
            if index:
                row_contents.append({"type": "separator", "color": "#eadfd4"})
            row_contents.append(self._info_row(row[0], row[1]))

        return {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": header_color,
                "paddingAll": "18px",
                "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "lg", "color": "#ffffff", "wrap": True},
                    {"type": "text", "text": subtitle or "-", "size": "sm", "color": "#fff6e8", "margin": "sm", "wrap": True},
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "backgroundColor": "#fffaf2",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "md",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": status_tint,
                                "cornerRadius": "10px",
                                "paddingAll": "12px",
                                "flex": 2,
                                "contents": [
                                    {"type": "text", "text": "目前狀態", "size": "xs", "color": "#6f645c"},
                                    {
                                        "type": "text",
                                        "text": status,
                                        "size": "md",
                                        "weight": "bold",
                                        "color": status_color,
                                        "wrap": True,
                                        "margin": "xs",
                                    },
                                ],
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": status_color,
                                "cornerRadius": "10px",
                                "paddingAll": "12px",
                                "flex": 1,
                                "alignItems": "center",
                                "justifyContent": "center",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "通知",
                                        "size": "sm",
                                        "weight": "bold",
                                        "color": "#ffffff",
                                        "align": "center",
                                    }
                                ],
                            },
                        ],
                    },
                    {"type": "separator", "color": "#eadfd4"},
                    *row_contents,
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#fffaf2",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "button",
                        "height": "sm",
                        "style": "primary",
                        "color": footer_color,
                        "action": {"type": "uri", "label": action_label, "uri": self._frontend_url(action_path)},
                    }
                ],
            },
        }

    def _adoption_bubble(self, order, event_name):
        animal = order.warm_paws_animal_product_id
        status = self._adoption_stage_label(event_name)
        action_path = "/profile/records" if event_name == "completed" else "/profile/applications"
        action_label = "查看我的認養紀錄" if event_name == "completed" else "查看我的認養申請"
        rows = [
            ("毛孩", animal.name if animal else "-"),
            ("品種", animal.animal_breed if animal else "-"),
            ("申請人", order.partner_id.name or "-"),
            ("電話", order.warm_paws_applicant_phone or order.partner_id.phone or "-"),
            ("居住縣市", order.warm_paws_applicant_city or "-"),
        ]
        return self._warm_card(
            "暖心毛孩認養申請提醒",
            order.name,
            status,
            rows,
            action_label,
            action_path,
            "#5f9f78",
            "#237a55",
            event_name,
        )

    def _visit_bubble(self, event, event_name):
        animal = event.warm_paws_animal_product_id
        partner = event.partner_ids[:1]
        animal_name = animal.name if animal else "-"
        applicant = partner.name if partner else "-"
        rows = [
            ("毛孩", animal_name),
            ("訪視時間", self._plain_datetime(event.start)),
            ("聯絡電話", event.warm_paws_phone or (partner.phone if partner else "-") or "-"),
            ("備註", event.warm_paws_note or "-"),
        ]
        return self._warm_card(
            "暖心毛孩訪視預約提醒",
            f"認養訪視：{animal_name} - {applicant}",
            self._visit_stage_label(event_name),
            rows,
            "查看預約詳情",
            "/profile/appointments",
            "#7b5439",
            "#7b5439",
            event_name,
        )

    def notify_adoption(self, order, event_name):
        order = order.sudo()
        if not order.partner_id:
            return False
        bubble = self._adoption_bubble(order, event_name)
        return self.push_flex(order.partner_id, f"認養申請{self._adoption_stage_label(event_name)}", bubble)

    def notify_visit(self, event, event_name="created"):
        event = event.sudo()
        partners = event.partner_ids.filtered(lambda partner: partner.warm_paws_line_user_id)
        if not partners:
            return False
        bubble = self._visit_bubble(event, event_name)
        sent = False
        for partner in partners:
            sent = self.push_flex(partner, self._visit_stage_label(event_name), bubble) or sent
        return sent
