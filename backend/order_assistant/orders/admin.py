from django.contrib import admin
from django.urls import path
from django.utils import timezone

from .models import PriceBook, Quote, Requirement, RequirementRound


class RequirementRoundInline(admin.TabularInline):
    model = RequirementRound
    extra = 0
    fields = ("round_no", "deadline_days", "change_note", "submitted_at")
    readonly_fields = ("submitted_at",)
    ordering = ("round_no",)
    show_change_link = True


@admin.register(PriceBook)
class PriceBookAdmin(admin.ModelAdmin):
    list_display = ("category", "label", "day_rate", "base_days", "active", "updated_at")
    list_editable = ("day_rate", "base_days", "active")
    search_fields = ("category", "label")


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "client_name",
        "category_label_display",
        "status_label_display",
        "current_round",
        "latest_price_display",
        "updated_at",
    )
    list_filter = ("status", "category")
    search_fields = ("title", "client_name", "contact", "public_id", "description")
    readonly_fields = ("public_id", "current_round", "created_at", "updated_at")
    inlines = [RequirementRoundInline]
    fieldsets = (
        (
            "需求信息",
            {
                "fields": (
                    "title",
                    "client_name",
                    "contact",
                    "category",
                    "description",
                    "deliverables",
                    "deadline_days",
                    "budget_expectation",
                    "notes",
                )
            },
        ),
        ("状态", {"fields": ("status", "current_round", "public_id", "created_at", "updated_at")}),
    )

    @admin.display(description="类别")
    def category_label_display(self, obj):
        return obj.category_label

    @admin.display(description="状态")
    def status_label_display(self, obj):
        return obj.status_label

    @admin.display(description="最新建议价")
    def latest_price_display(self, obj):
        round_obj = obj.rounds.order_by("-round_no").first()
        quote = getattr(round_obj, "quote", None) if round_obj else None
        return f"¥{quote.effective_amount:,}" if quote else "—"


@admin.register(RequirementRound)
class RequirementRoundAdmin(admin.ModelAdmin):
    list_display = ("requirement", "round_no", "deadline_days", "change_note", "submitted_at")
    list_filter = ("round_no",)
    search_fields = ("requirement__title", "requirement__public_id", "change_note")
    readonly_fields = ("submitted_at",)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        "quote_no",
        "requirement_display",
        "round_no_display",
        "suggested_price",
        "range_display",
        "confidence",
        "status",
        "generated_at",
    )
    list_filter = ("status", "pricing_version")
    search_fields = ("quote_no", "round__requirement__title", "round__requirement__public_id")
    readonly_fields = (
        "quote_no",
        "round",
        "currency",
        "amount_min",
        "amount_max",
        "suggested_price",
        "confidence",
        "pricing_version",
        "market_basis",
        "breakdown",
        "assumptions",
        "generated_at",
    )
    fieldsets = (
        (
            "报价",
            {
                "fields": (
                    "quote_no",
                    "round",
                    "currency",
                    "amount_min",
                    "amount_max",
                    "suggested_price",
                    "confidence",
                    "pricing_version",
                    "generated_at",
                )
            },
        ),
        ("依据", {"fields": ("market_basis", "breakdown", "assumptions")}),
        ("人工调整", {"fields": ("status", "adjusted_amount", "adjust_reason")}),
    )

    @admin.display(description="需求")
    def requirement_display(self, obj):
        return obj.round.requirement.title

    @admin.display(description="轮次")
    def round_no_display(self, obj):
        return obj.round.round_no

    @admin.display(description="区间")
    def range_display(self, obj):
        return f"¥{obj.amount_min:,} – ¥{obj.amount_max:,}"

    def save_model(self, request, obj, form, change):
        if obj.adjusted_amount:
            obj.status = "adjusted"
        super().save_model(request, obj, form, change)


def dashboard_view(request):
    now = timezone.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    requirements = list(Requirement.objects.all().order_by("-updated_at")[:20])
    quotes = list(
        Quote.objects.select_related("round__requirement").order_by("-generated_at")[:20]
    )

    from django.urls import reverse

    requirement_rows = []
    for item in requirements:
        latest_round = item.rounds.order_by("-round_no").first()
        quote = getattr(latest_round, "quote", None) if latest_round else None
        requirement_rows.append(
            {
                "id": item.id,
                "title": item.title,
                "client_name": item.client_name or "—",
                "category": item.category_label,
                "status": item.status_label,
                "round": item.current_round,
                "price": quote.effective_amount if quote else None,
                "price_text": f"¥{quote.effective_amount:,}" if quote else "—",
                "updated_at": timezone.localtime(item.updated_at).strftime("%m-%d %H:%M"),
                "admin_url": reverse("admin:orders_requirement_change", args=[item.id]),
            }
        )
    quote_rows = []
    for quote in quotes:
        quote_rows.append(
            {
                "id": quote.id,
                "quote_no": quote.quote_no,
                "title": quote.round.requirement.title,
                "round": quote.round.round_no,
                "suggested_price": quote.effective_amount,
                "price_text": f"¥{quote.effective_amount:,}",
                "range_text": f"¥{quote.amount_min:,} – ¥{quote.amount_max:,}",
                "amount_min": quote.amount_min,
                "amount_max": quote.amount_max,
                "status": quote.get_status_display(),
                "generated_at": timezone.localtime(quote.generated_at).strftime("%m-%d %H:%M"),
                "admin_url": reverse("admin:orders_quote_change", args=[quote.id]),
            }
        )

    stats = {
        "requirements": Requirement.objects.count(),
        "quoted": Requirement.objects.filter(status="quoted").count(),
        "active": Requirement.objects.filter(
            status__in=["confirmed", "in_progress"]
        ).count(),
        "month_amount": sum(
            q.effective_amount
            for q in Quote.objects.filter(generated_at__gte=month_start)
        ),
    }
    context = {
        **admin.site.each_context(request),
        "title": "接单看板",
        "stats": stats,
        "requirements": requirement_rows,
        "quotes": quote_rows,
        "dashboard_data": {
            "requirements": requirement_rows,
            "quotes": quote_rows,
            "stats": stats,
        },
    }
    from django.shortcuts import render

    return render(request, "admin/order_dashboard.html", context)


_original_get_urls = admin.site.get_urls


def _get_urls():
    custom = [
        path("dashboard/", admin.site.admin_view(dashboard_view), name="order_dashboard")
    ]
    return custom + _original_get_urls()


admin.site.get_urls = _get_urls
admin.site.site_header = "接单管理后台"
admin.site.site_title = "接单管理后台"
admin.site.index_title = "需求与报价"
