from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    warm_paws_line_liff_id = fields.Char(
        string="LINE LIFF ID",
        config_parameter="warm_paws.line_liff_id",
        default="2010432240-mRjM2C9g",
    )
    warm_paws_line_channel_id = fields.Char(
        string="LINE Login Channel ID",
        config_parameter="warm_paws.line_channel_id",
        default="2010432240",
    )
    warm_paws_line_messaging_channel_id = fields.Char(
        string="LINE Messaging Channel ID",
        config_parameter="warm_paws.line_messaging_channel_id",
        default="2010436798",
    )
    warm_paws_line_channel_secret = fields.Char(
        string="LINE Channel Secret",
        config_parameter="warm_paws.line_channel_secret",
        default="bf05c9d3ce67431396ba4fae95201abd",
    )
    warm_paws_line_channel_access_token = fields.Char(
        string="LINE Channel Access Token",
        config_parameter="warm_paws.line_channel_access_token",
    )
    warm_paws_line_liff_url = fields.Char(
        string="LINE LIFF URL",
        config_parameter="warm_paws.line_liff_url",
        default="https://liff.line.me/2010432240-mRjM2C9g",
    )
    warm_paws_frontend_url = fields.Char(
        string="Frontend URL",
        config_parameter="warm_paws.frontend_url",
        default="https://adoption-platform.zeabur.app",
    )
