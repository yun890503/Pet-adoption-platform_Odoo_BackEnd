import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from odoo import models

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
            "messages": [
                {
                    "type": "flex",
                    "altText": alt_text,
                    "contents": bubble,
                }
            ],
        }
        request = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps(payload).encode("utf-8"),
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
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            _logger.warning("LINE push failed for partner %s: %s", partner.id, error)
            return False

    def _frontend_url(self, path):
        base = self._param("frontend_url", "https://adoption-platform.zeabur.app").rstrip("/")
        return f"{base}{path}"

    def _info_row(self, label, value):
        return {
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": label, "color": "#8a5a35", "size": "sm", "flex": 2},
                {"type": "text", "text": str(value or "-"), "color": "#2b2118", "size": "sm", "wrap": True, "flex": 5},
            ],
        }

    def warm_card(self, title, subtitle, status, rows, action_label, action_path, status_color="#ff8a3d"):
        return {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#744d32",
                "paddingAll": "18px",
                "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "lg", "color": "#ffffff", "wrap": True},
                    {"type": "text", "text": subtitle or "暖心毛孩認養中心", "size": "sm", "color": "#fff1df", "margin": "sm", "wrap": True},
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "backgroundColor": "#fffaf2",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "md",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": "#f8ead5",
                                "cornerRadius": "10px",
                                "paddingAll": "12px",
                                "flex": 2,
                                "contents": [
                                    {"type": "text", "text": "目前狀態", "size": "xs", "color": "#8a5a35"},
                                    {"type": "text", "text": status, "size": "md", "weight": "bold", "color": "#2b2118", "wrap": True},
                                ],
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": status_color,
                                "cornerRadius": "10px",
                                "paddingAll": "12px",
                                "alignItems": "center",
                                "justifyContent": "center",
                                "flex": 1,
                                "contents": [
                                    {"type": "text", "text": "通知", "size": "sm", "weight": "bold", "color": "#ffffff"},
                                ],
                            },
                        ],
                    },
                    {"type": "separator", "color": "#ead9bf"},
                    *[self._info_row(row[0], row[1]) for row in rows],
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#fffaf2",
                "contents": [
                    {
                        "type": "button",
                        "height": "sm",
                        "style": "primary",
                        "color": "#744d32",
                        "action": {"type": "uri", "label": action_label, "uri": self._frontend_url(action_path)},
                    }
                ],
            },
        }

    def notify_adoption(self, order, event_name):
        order = order.sudo()
        if not order.partner_id:
            return False
        animal = order.warm_paws_animal_product_id
        stage_label = {
            "created": "已收到申請",
            "reviewing": "審核中",
            "approved": "已通過",
            "completed": "已完成認養",
            "cancelled": "已取消",
        }.get(event_name, "審核中")
        color = {
            "created": "#ff8a3d",
            "reviewing": "#f6a623",
            "approved": "#19c28b",
            "completed": "#7fb069",
            "cancelled": "#9ca3af",
        }.get(event_name, "#ff8a3d")
        bubble = self.warm_card(
            "暖心毛孩認養申請提醒",
            order.name,
            stage_label,
            [
                ("毛孩", animal.name if animal else ""),
                ("品種", animal.animal_breed if animal else ""),
                ("申請人", order.partner_id.name),
                ("電話", order.warm_paws_applicant_phone),
                ("居住縣市", order.warm_paws_applicant_city),
            ],
            "查看我的認養申請",
            "/profile/applications",
            color,
        )
        return self.push_flex(order.partner_id, f"認養申請{stage_label}", bubble)

    def notify_visit(self, event, event_name="created"):
        event = event.sudo()
        partners = event.partner_ids.filtered(lambda partner: partner.warm_paws_line_user_id)
        if not partners:
            return False
        animal = event.warm_paws_animal_product_id
        status = "已新增預約" if event_name == "created" else "預約已取消"
        color = "#19c28b" if event_name == "created" else "#9ca3af"
        bubble = self.warm_card(
            "暖心毛孩訪視預約提醒",
            event.name,
            status,
            [
                ("毛孩", animal.name if animal else ""),
                ("訪視時間", event.start),
                ("電話", event.warm_paws_phone),
                ("備註", event.warm_paws_note),
            ],
            "查看預約訪視",
            "/profile/appointments",
            color,
        )
        sent = False
        for partner in partners:
            sent = self.push_flex(partner, status, bubble) or sent
        return sent
