import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Quote, Requirement, RequirementRound
from .pricing import catalog_map, estimate, price_modules


def llm_result(modules, confidence=0.82):
    return {
        "ok": True,
        "modules": modules,
        "summary": "测试用 LLM 拆解",
        "confidence": confidence,
        "assumptions": ["测试假设"],
        "model": "test-model",
        "latency_ms": 120,
        "raw": {"content": "{}"},
    }


BASE_MODULES = [
    {"name": "前端页面", "description": "页面与交互", "category": "frontend", "days": 4, "complexity": 1.0},
    {"name": "管理后台", "description": "后台功能", "category": "backend", "days": 5, "complexity": 1.1},
    {"name": "权限与账号", "description": "登录与权限", "category": "backend", "days": 3, "complexity": 1.0},
]


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
        self.assertGreaterEqual(len(result.breakdown), 4)
        self.assertTrue(any(item.get("kind") == "module" for item in result.breakdown))
        self.assertTrue(any(item.get("kind") == "overhead" for item in result.breakdown))

    def test_more_module_days_costs_more(self):
        catalog = catalog_map()
        small = price_modules(
            modules=[{"name": "核心功能", "category": "backend", "days": 3, "complexity": 1.0}],
            catalog=catalog,
            decomposition_source="llm",
        )
        large = price_modules(
            modules=[{"name": "核心功能", "category": "backend", "days": 8, "complexity": 1.2}],
            catalog=catalog,
            decomposition_source="llm",
        )
        self.assertGreater(large.suggested_price, small.suggested_price)
        self.assertGreater(large.total_days, small.total_days)
        self.assertEqual(sum(item["amount"] for item in large.breakdown), large.suggested_price)


class ApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.llm_patcher = patch("orders.llm.decompose")
        self.mock_llm = self.llm_patcher.start()
        self.mock_llm.return_value = llm_result(BASE_MODULES)
        self.addCleanup(self.llm_patcher.stop)

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
        self.assertEqual(response.json()["pricing_version"], "market-2026.2")
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
        self.assertEqual(quote["decomposition_source"], "llm")
        self.assertEqual(quote["module_count"], 3)
        self.assertEqual(len(quote["modules"]), 3)

    def test_fallback_when_llm_fails(self):
        self.mock_llm.return_value = {"ok": False, "error": "timeout"}
        response = self.create_requirement()
        self.assertEqual(response.status_code, 201)
        quote = response.json()["latest_quote"]
        self.assertEqual(quote["decomposition_source"], "fallback")
        self.assertGreaterEqual(quote["module_count"], 1)
        self.assertTrue(any(item.get("kind") == "module" for item in quote["breakdown"]))

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
        second_modules = BASE_MODULES + [
            {"name": "支付与订单", "description": "支付、订单与对账", "category": "backend", "days": 4, "complexity": 1.2}
        ]
        self.mock_llm.side_effect = [llm_result(BASE_MODULES), llm_result(second_modules)]
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
            any("新增模块" in reason for reason in data["comparison"]["reasons"]),
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
