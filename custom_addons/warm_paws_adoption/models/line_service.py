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

    def _backend_url(self):
        base = (
            self._param("backend_url")
            or os.environ.get("BACKEND_URL")
            or self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            or "https://heartwarming.zeabur.app"
        )
        return base.rstrip("/")

    def _animal_image_url(self, animal):
        if not animal:
            return ""
        return f"{self._backend_url()}/web/image/product.template/{animal.id}/image_512"

    def _plain_datetime(self, value):
        if not value:
            return "-"
        try:
            dt_value = fields.Datetime.context_timestamp(self, value)
            return dt_value.strftime("%Y/%m/%d %H:%M")
        except Exception:
            return str(value)

    def _info_row(self, label, value, icon=""):
        icon_box = {
            "type": "box",
            "layout": "vertical",
            "width": "32px",
            "height": "32px",
            "cornerRadius": "16px",
            "backgroundColor": "#eaf6ef",
            "alignItems": "center",
            "justifyContent": "center",
            "contents": [{"type": "text", "text": icon or "•", "size": "sm", "align": "center", "color": "#2f7d5a"}],
        }
        return {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "paddingTop": "8px",
            "paddingBottom": "8px",
            "contents": [
                icon_box,
                {"type": "text", "text": label, "color": "#2f7d5a", "size": "sm", "flex": 2, "gravity": "center"},
                {
                    "type": "text",
                    "text": str(value or "-"),
                    "color": "#2b2118",
                    "size": "sm",
                    "wrap": True,
                    "flex": 4,
                    "gravity": "center",
                },
            ],
        }

    def _status_color(self, event_name, kind):
        if event_name in ("approved", "completed", "created"):
            return "#2f8f67"
        if event_name == "cancelled":
            return "#d94343" if kind == "visit" else "#8b8f98"
        if event_name == "reviewing":
            return "#d7952c"
        return "#ff8a3d"

    def _adoption_stage_label(self, event_name):
        return {
            "created": "已收到申請",
            "reviewing": "審核中",
            "approved": "已通過",
            "completed": "已完成認養",
            "cancelled": "已取消",
        }.get(event_name, "審核中")

    def _visit_stage_label(self, event_name):
        return "預約已取消" if event_name == "cancelled" else "預約成功"

    def _adoption_bubble(self, order, event_name):
        animal = order.warm_paws_animal_product_id
        status = self._adoption_stage_label(event_name)
        status_color = self._status_color(event_name, "adoption")
        action_path = "/profile/records" if event_name == "completed" else "/profile/applications"
        action_label = "查看我的認養紀錄" if event_name == "completed" else "查看我的認養申請"

        rows = [
            ("毛孩", animal.name if animal else "-", "👤"),
            ("品種", animal.animal_breed if animal else "-", "🐾"),
            ("申請人", order.partner_id.name or "-", "👤"),
            ("電話", order.warm_paws_applicant_phone or order.partner_id.phone or "-", "☎"),
            ("居住縣市", order.warm_paws_applicant_city or "-", "⌖"),
        ]
        return self._green_bubble(
            title="暖心毛孩認養申請提醒",
            subtitle=order.name,
            status=status,
            status_color=status_color,
            rows=rows,
            action_label=action_label,
            action_path=action_path,
        )

    def _visit_bubble(self, event, event_name):
        animal = event.warm_paws_animal_product_id
        partner = event.partner_ids[:1]
        status = self._visit_stage_label(event_name)
        status_color = self._status_color(event_name, "visit")
        animal_name = animal.name if animal else "-"
        applicant = partner.name if partner else "-"
        rows = [
            ("毛孩", animal_name, "🐾"),
            ("訪視時間", self._plain_datetime(event.start), "📅"),
            ("聯絡電話", event.warm_paws_phone or (partner.phone if partner else "-") or "-", "☎"),
            ("備註", event.warm_paws_note or "-", "▤"),
        ]
        return self._brown_bubble(
            title="暖心毛孩訪視預約提醒",
            subtitle=f"認養訪視：{animal_name} - {applicant}",
            status=status,
            status_color=status_color,
            image_url=self._animal_image_url(animal),
            rows=rows,
            action_label="查看預約詳情",
            action_path="/profile/appointments",
            reschedule_label="重新安排訪視",
        )

    def _green_bubble(self, title, subtitle, status, status_color, rows, action_label, action_path):
        row_contents = []
        for index, row in enumerate(rows):
            if index:
                row_contents.append({"type": "separator", "color": "#dce9df"})
            row_contents.append(self._info_row(row[0], row[1], row[2]))

        return {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "paddingAll": "20px",
                "backgroundColor": "#65aa82",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "flex": 3,
                        "contents": [
                            {"type": "text", "text": title, "weight": "bold", "size": "xl", "color": "#ffffff", "wrap": True},
                            {"type": "separator", "color": "#b8dcc8", "margin": "md"},
                            {"type": "text", "text": subtitle or "-", "size": "md", "color": "#edf8f1", "margin": "md", "wrap": True},
                        ],
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "flex": 2,
                        "alignItems": "center",
                        "justifyContent": "center",
                        "contents": [{"type": "text", "text": "🐶🐱", "size": "xxl", "align": "center"}],
                    },
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "backgroundColor": "#ffffff",
                "paddingAll": "18px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "md",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "md",
                                "backgroundColor": "#eef8f2",
                                "cornerRadius": "14px",
                                "paddingAll": "14px",
                                "flex": 3,
                                "contents": [
                                    {"type": "text", "text": "✓", "size": "xxl", "color": status_color, "flex": 1, "gravity": "center"},
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "flex": 3,
                                        "contents": [
                                            {"type": "text", "text": "目前狀態", "size": "sm", "color": "#4b6356"},
                                            {"type": "text", "text": status, "size": "xl", "weight": "bold", "color": status_color, "wrap": True},
                                        ],
                                    },
                                ],
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "backgroundColor": status_color,
                                "cornerRadius": "14px",
                                "paddingAll": "14px",
                                "flex": 2,
                                "alignItems": "center",
                                "justifyContent": "center",
                                "spacing": "sm",
                                "contents": [
                                    {"type": "text", "text": "🔔", "size": "lg", "color": "#ffffff", "flex": 0},
                                    {"type": "text", "text": "通知", "size": "md", "weight": "bold", "color": "#ffffff", "align": "center"},
                                ],
                            },
                        ],
                    },
                    {"type": "separator", "color": "#dce9df", "margin": "md"},
                    *row_contents,
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#ffffff",
                "paddingAll": "18px",
                "contents": [
                    {
                        "type": "button",
                        "height": "md",
                        "style": "primary",
                        "color": "#237a55",
                        "action": {"type": "uri", "label": action_label, "uri": self._frontend_url(action_path)},
                    }
                ],
            },
        }

    def _brown_bubble(self, title, subtitle, status, status_color, image_url, rows, action_label, action_path, reschedule_label):
        row_contents = []
        for index, row in enumerate(rows):
            if index:
                row_contents.append({"type": "separator", "color": "#eadfd4"})
            row_contents.append(self._info_row(row[0], row[1], row[2]))

        status_description = (
            "此預約已取消，若需重新安排，請點擊下方按鈕。"
            if status == "預約已取消"
            else "我們已收到您的訪視預約，請準時抵達中途之家。"
        )
        body_contents = [
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "md",
                "backgroundColor": "#fff2ef" if status == "預約已取消" else "#eef8f2",
                "cornerRadius": "14px",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": "✕" if status == "預約已取消" else "✓", "size": "xl", "color": status_color, "flex": 0},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": status, "size": "xl", "weight": "bold", "color": status_color},
                            {"type": "text", "text": status_description, "size": "sm", "color": "#6f645c", "wrap": True, "margin": "sm"},
                        ],
                    },
                ],
            },
            {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#ffffff",
                "cornerRadius": "16px",
                "paddingAll": "14px",
                "spacing": "sm",
                "contents": row_contents,
            },
        ]

        if status == "預約已取消":
            body_contents.append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "backgroundColor": "#f7f1e9",
                    "cornerRadius": "14px",
                    "paddingAll": "12px",
                    "spacing": "md",
                    "contents": [
                        {"type": "text", "text": "↻", "size": "xl", "color": "#2f8f67", "flex": 0, "gravity": "center"},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 2,
                            "contents": [
                                {"type": "text", "text": "需要重新安排訪視？", "size": "md", "weight": "bold", "color": "#2f8f67"},
                                {"type": "text", "text": "點擊按鈕重新選擇訪視時間", "size": "xs", "color": "#6f645c", "wrap": True},
                            ],
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "height": "sm",
                            "color": "#2f8f67",
                            "action": {"type": "uri", "label": reschedule_label, "uri": self._frontend_url("/profile/appointments")},
                            "flex": 2,
                        },
                    ],
                }
            )

        header_contents = [
            {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "xl", "color": "#ffffff", "wrap": True},
                    {"type": "text", "text": subtitle or "-", "size": "sm", "color": "#fff1df", "margin": "sm", "wrap": True},
                ],
            }
        ]

        if image_url:
            header_contents.append(
                {
                    "type": "image",
                    "url": image_url,
                    "size": "md",
                    "aspectRatio": "1:1",
                    "aspectMode": "cover",
                    "cornerRadius": "999px",
                    "margin": "lg",
                }
            )

        return {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "backgroundColor": "#7b5439",
                "paddingAll": "20px",
                "spacing": "md",
                "contents": header_contents,
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#fff8ef",
                "paddingAll": "18px",
                "spacing": "md",
                "contents": body_contents,
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#fff8ef",
                "paddingAll": "18px",
                "contents": [
                    {
                        "type": "button",
                        "height": "md",
                        "style": "secondary",
                        "color": "#7b5439",
                        "action": {"type": "uri", "label": action_label, "uri": self._frontend_url(action_path)},
                    }
                ],
            },
        }

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
