import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Quote, Requirement, RequirementRound
from .pricing import estimate


class PricingTests(TestCase):
    def test_same_input_same_output(self):
        kwargs = dict(
            title="企业官网改版",
            description="需要重做 PC 官网与后台管理，包含新闻、产品、表单与权限。",
            deliverables=["PC 端", "后台管理"],
            deadline_days=30,
            budget_expectation=50000,
            contact="a@b.com",
            category="web_fullstack",
        )
        first = estimate(**kwargs)
        second = estimate(**kwargs)
        self.assertEqual(first.suggested_price, second.suggested_price)
        self.assertEqual(first.amount_min, second.amount_min)
        self.assertEqual(first.breakdown, second.breakdown)

    def test_range_and_breakdown(self):
        result = estimate(
            title="小程序商城",
            description="做一个带商品、订单、支付和会员的小程序商城，需要对接微信支付。",
            deliverables=["小程序", "后台", "支付"],
            deadline_days=20,
            category="miniprogram",
        )
        self.assertLess(result.amount_min, result.suggested_price)
        self.assertLess(result.suggested_price, result.amount_max)
        total = sum(item["amount"] for item in result.breakdown)
        self.assertLessEqual(abs(total - result.suggested_price), 2)
        self.assertEqual(len(result.breakdown), 5)

    def test_more_complex_costs_more(self):
        simple = estimate(
            title="简单脚本",
            description="写一个定时备份脚本。" * 3,
            deliverables=["脚本"],
            deadline_days=30,
            category="automation",
        )
        complex_ = estimate(
            title="复杂自动化",
            description=(
                "需要自动化脚本，支持权限、支付、第三方对接、多端、实时、高并发、迁移、国际化、审批。"
                * 6
            ),
            deliverables=["脚本", "后台", "监控", "文档", "部署"],
            deadline_days=10,
            category="automation",
        )
        self.assertGreater(complex_.suggested_price, simple.suggested_price)
        self.assertGreater(complex_.complexity, simple.complexity)


class ApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def create_requirement(self, **overrides):
        payload = {
            "title": "企业官网改版",
            "client_name": "张三",
            "contact": "zhang@example.com",
            "category": "web_fullstack",
            "description": "重做公司官网与后台管理，包含产品、新闻、表单和权限管理。",
            "deliverables": ["PC 端", "后台管理"],
            "deadline_days": 30,
            "budget_expectation": 50000,
            "notes": "希望 11 月上线",
        }
        payload.update(overrides)
        return self.client.post(
            "/api/order/requirements",
            data=json.dumps(payload, ensure_ascii=False),
            content_type="application/json",
        )

    def test_health_and_meta(self):
        response = self.client.get("/api/order/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pricing_version"], "market-2026.1")
        meta = self.client.get("/api/order/meta").json()
        self.assertTrue(any(item["key"] == "web_fullstack" for item in meta["categories"]))

    def test_create_requirement_generates_quote(self):
        response = self.create_requirement()
        self.assertEqual(response.status_code, 201, response.content.decode())
        data = response.json()
        self.assertEqual(data["current_round"], 1)
        self.assertEqual(len(data["rounds"]), 1)
        quote = data["latest_quote"]
        self.assertLess(quote["amount_min"], quote["suggested_price"])
        self.assertLess(quote["suggested_price"], quote["amount_max"])
        self.assertEqual(quote["round_no"], 1)
        self.assertTrue(quote["market_basis"])
        self.assertEqual(Requirement.objects.count(), 1)
        self.assertEqual(RequirementRound.objects.count(), 1)
        self.assertEqual(Quote.objects.count(), 1)

    def test_patch_does_not_create_new_quote(self):
        created = self.create_requirement().json()
        public_id = created["public_id"]
        response = self.client.patch(
            f"/api/order/requirements/{public_id}",
            data=json.dumps({"title": "官网改版二期", "deadline_days": 40}, ensure_ascii=False),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "官网改版二期")
        self.assertEqual(response.json()["deadline_days"], 40)
        self.assertEqual(Quote.objects.count(), 1)

    def test_second_round_reprices_with_comparison(self):
        created = self.create_requirement().json()
        public_id = created["public_id"]
        first_price = created["latest_quote"]["suggested_price"]
        response = self.client.post(
            f"/api/order/requirements/{public_id}/rounds",
            data=json.dumps(
                {
                    "description": "在官网基础上新增支付、会员与优惠券，后台增加审批流程。",
                    "deliverables": ["PC 端", "后台管理", "支付", "会员"],
                    "deadline_days": 35,
                    "change_note": "新增支付与会员",
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content.decode())
        data = response.json()
        self.assertEqual(data["round"]["round_no"], 2)
        self.assertEqual(data["requirement"]["current_round"], 2)
        self.assertEqual(len(data["requirement"]["rounds"]), 2)
        self.assertEqual(Quote.objects.count(), 2)
        self.assertEqual(data["comparison"]["previous_suggested_price"], first_price)
        self.assertNotEqual(data["quote"]["suggested_price"], first_price)
        self.assertTrue(data["comparison"]["reasons"])
        self.assertTrue(
            any("交付物" in reason for reason in data["comparison"]["reasons"]),
            data["comparison"]["reasons"],
        )

    def test_validation_errors(self):
        response = self.create_requirement(title="", description="短", deadline_days=-3)
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"], "validation_error")
        self.assertIn("title", payload["fields"])
        self.assertIn("description", payload["fields"])
        self.assertIn("deadline_days", payload["fields"])

    def test_public_list_requires_ids_and_hides_private_fields(self):
        created = self.create_requirement().json()
        response = self.client.get("/api/order/requirements")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "missing_ids")

        response = self.client.get(
            f"/api/order/requirements?ids={created['public_id']},req_missing"
        )
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertNotIn("contact", items[0])
        self.assertNotIn("notes", items[0])

    def test_status_transitions(self):
        created = self.create_requirement().json()
        public_id = created["public_id"]
        response = self.client.post(
            f"/api/order/requirements/{public_id}/status",
            data=json.dumps({"status": "confirmed"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "confirmed")
        response = self.client.post(
            f"/api/order/requirements/{public_id}/status",
            data=json.dumps({"status": "quoted"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)

    def test_unknown_requirement_404(self):
        self.assertEqual(
            self.client.get("/api/order/requirements/req_nope").status_code, 404
        )


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_superuser("admin", "admin@example.com", "test-pass-123")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("admin:order_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_with_elementui(self):
        self.client.login(username="admin", password="test-pass-123")
        response = self.client.get(reverse("admin:order_dashboard"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("接单看板", html)
        self.assertIn("element-ui/index.js", html)
        self.assertIn("el-table", html)
