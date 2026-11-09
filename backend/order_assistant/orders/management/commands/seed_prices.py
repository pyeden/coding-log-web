from django.core.management.base import BaseCommand

from orders.models import PriceBook
from orders.pricing import DEFAULT_CATALOG


class Command(BaseCommand):
    help = "Seed or update the market price book."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for item in DEFAULT_CATALOG:
            obj, is_new = PriceBook.objects.update_or_create(
                category=item["category"],
                defaults={
                    "label": item["label"],
                    "day_rate": item["day_rate"],
                    "base_days": item["base_days"],
                    "keywords": item["keywords"],
                    "active": True,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"pricebook seeded: created={created} updated={updated}")
        )
