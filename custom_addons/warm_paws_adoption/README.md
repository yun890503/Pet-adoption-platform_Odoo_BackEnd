# Warm Paws Adoption Odoo Backend

Odoo 18 custom addon for the Warm Paws pet adoption platform.

## Features

- Extends Sales products as adoptable pet profiles.
- Adds adoption-specific product fields, including breed, age, gender, health, story, traits, suitable homes, and adoption photos.
- Stores adoption page photos in Odoo database image fields.
- Provides JSON API endpoints for the React frontend.
- Records adoption inquiries, volunteer applications, contact messages, members, and favorites.

## Install

1. Put this folder in an Odoo 18 `custom_addons` directory.
2. Add the custom addons directory to `addons_path`.
3. Update the app list in Odoo.
4. Install `Warm Paws Adoption`.

Example upgrade command:

```bash
python odoo-bin -c path/to/odoo.conf -d Pet-adoption-platform -u warm_paws_adoption
```
