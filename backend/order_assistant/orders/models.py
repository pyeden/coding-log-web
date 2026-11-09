import secrets

from django.db import models
from django.utils import timezone


def new_public_id():
    return "req_" + secrets.token_hex(16)


class PriceBook(models.Model):
    """市场人日价基线，可在 Django admin 中维护。"""

    category = models.CharField("类别 key", max_length=32, unique=True)
    label = models.CharField("类别名称", max_length=40)
    day_rate = models.PositiveIntegerField("人日价（元）")
    base_days = models.PositiveIntegerField("基础工作量（人日）")
    keywords = models.JSONField("识别关键词", default=list, blank=True)
    active = models.BooleanField("启用", default=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "市场价目"
        verbose_name_plural = "市场价目"
        ordering = ["category"]

    def __str__(self):
        return f"{self.label} · {self.day_rate} 元/人日"


class Requirement(models.Model):
    STATUS_CHOICES = [
        ("quoted", "已报价"),
        ("confirmed", "已确认"),
        ("in_progress", "进行中"),
        ("closed", "已结单"),
        ("cancelled", "已取消"),
    ]

    public_id = models.CharField(
        "公开 ID", max_length=40, unique=True, default=new_public_id, editable=False
    )
    title = models.CharField("项目名称", max_length=120)
    client_name = models.CharField("客户 / 联系人", max_length=80, blank=True)
    contact = models.CharField("联系方式", max_length=120, blank=True)
    category = models.CharField("需求类别", max_length=32, default="other")
    description = models.TextField("需求描述")
    deliverables = models.JSONField("交付物", default=list, blank=True)
    deadline_days = models.PositiveIntegerField("期望工期（天）", default=30)
    budget_expectation = models.PositiveIntegerField("预算参考（元）", null=True, blank=True)
    notes = models.TextField("备注", blank=True)
    status = models.CharField(
        "状态", max_length=20, choices=STATUS_CHOICES, default="quoted"
    )
    current_round = models.PositiveIntegerField("当前轮次", default=1)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "需求"
        verbose_name_plural = "需求"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title}（{self.public_id}）"

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def category_label(self):
        try:
            return self.pricebook.label
        except PriceBook.DoesNotExist:
            return self.category

    @property
    def pricebook(self):
        return PriceBook.objects.get(category=self.category)


class RequirementRound(models.Model):
    requirement = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, related_name="rounds", verbose_name="需求"
    )
    round_no = models.PositiveIntegerField("轮次")
    description = models.TextField("本轮需求描述")
    deliverables = models.JSONField("本轮交付物", default=list, blank=True)
    deadline_days = models.PositiveIntegerField("期望工期（天）")
    change_note = models.CharField("本轮变更说明", max_length=300, blank=True)
    modules = models.JSONField("功能模块拆解", default=list, blank=True)
    decomposition_source = models.CharField(
        "拆解来源",
        max_length=12,
        choices=[("llm", "LLM 拆解"), ("fallback", "规则拆解")],
        default="fallback",
    )
    decomposition_model = models.CharField("拆解模型", max_length=80, blank=True, default="")
    decomposition_summary = models.TextField("拆解摘要", blank=True, default="")
    submitted_at = models.DateTimeField("提交时间", default=timezone.now)

    class Meta:
        verbose_name = "需求轮次"
        verbose_name_plural = "需求轮次"
        ordering = ["requirement", "round_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["requirement", "round_no"], name="uniq_requirement_round"
            )
        ]

    def __str__(self):
        return f"{self.requirement.title} · 第 {self.round_no} 轮"


class Quote(models.Model):
    STATUS_CHOICES = [("auto", "自动报价"), ("adjusted", "人工调整")]

    round = models.OneToOneField(
        RequirementRound, on_delete=models.CASCADE, related_name="quote", verbose_name="轮次"
    )
    quote_no = models.CharField("报价单号", max_length=24, unique=True)
    currency = models.CharField("币种", max_length=8, default="CNY")
    amount_min = models.PositiveIntegerField("区间下限（元）")
    amount_max = models.PositiveIntegerField("区间上限（元）")
    suggested_price = models.PositiveIntegerField("建议价（元）")
    confidence = models.FloatField("置信度", default=0.6)
    pricing_version = models.CharField("报价版本", max_length=32, default="market-2026.1")
    market_basis = models.TextField("市场依据")
    breakdown = models.JSONField("分阶段明细", default=list, blank=True)
    assumptions = models.JSONField("报价假设", default=list, blank=True)
    decomposition_source = models.CharField("拆解来源", max_length=12, default="fallback")
    decomposition_model = models.CharField("拆解模型", max_length=80, blank=True, default="")
    module_count = models.PositiveIntegerField("模块数", default=0)
    llm_latency_ms = models.PositiveIntegerField("LLM 耗时（毫秒）", default=0)
    llm_raw = models.JSONField("LLM 原始返回", default=dict, blank=True)
    status = models.CharField("报价状态", max_length=12, choices=STATUS_CHOICES, default="auto")
    adjusted_amount = models.PositiveIntegerField("人工调整价（元）", null=True, blank=True)
    adjust_reason = models.CharField("调整原因", max_length=300, blank=True)
    generated_at = models.DateTimeField("生成时间", default=timezone.now)

    class Meta:
        verbose_name = "报价"
        verbose_name_plural = "报价"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.quote_no} · {self.suggested_price} 元"

    @property
    def effective_amount(self):
        return self.adjusted_amount or self.suggested_price
