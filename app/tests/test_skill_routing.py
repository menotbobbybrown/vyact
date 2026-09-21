import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services import skill_routing
from services.skill_routing import calculate_expression, calculation_context
from routers import skills


class ArithmeticTests(unittest.TestCase):
    def test_weighted_rate_and_exact_decimal(self):
        self.assertEqual(float(calculate_expression('(10+90)/(100+900)*100', '10 90 100 900')), 10)
        self.assertEqual(calculate_expression('(20+90)/(100+900)*100', '20 90 100 900'), '11')
        self.assertEqual(calculate_expression('0.1+0.2', '0.1 0.2'), '0.3')
        self.assertEqual(calculate_expression('10+90', 'values: 10,90'), '100')
        self.assertEqual(calculate_expression('1000/10', '1,000 visits; 10 groups'), '100')

    def test_rejects_code_and_unsupported_numbers(self):
        for expression in ['__import__("os").system("id")', '2**1000000', 'open("x")', '[1][0]', 'True+1', '999/100', '1/0']:
            with self.subTest(expression=expression), self.assertRaises((ValueError, ArithmeticError)):
                calculate_expression(expression, '2 100')

    def test_failed_plan_never_claims_verified_results(self):
        context = calculation_context('10 100', [{'expression': '200/100'}])
        self.assertIn('No arithmetic result was verified', context)


class IntentSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_intent_selection_injects_real_calculation(self):
        es = AsyncMock()
        es.search.return_value = {'hits': {'hits': [{'_id': 'builtin:data-validation', '_source': {
            'name': 'data-validation', 'description': 'Validate analysis', 'instructions': 'Validate.'}}]}}
        with patch.object(skills, 'get_es', return_value=es), patch.object(skills, 'route_local_skills', AsyncMock(return_value={
            'skills': ['builtin:data-validation'], 'calculations': [{'expression': '(10+90)/(100+900)*100'}]
        })), patch.object(skills, 'get_embedding', AsyncMock()) as embed:
            selected = await skills.match_skills('10 90 100 900')
        self.assertEqual(selected[0]['name'], 'data-validation')
        self.assertIn('backend calculator evaluated', selected[0]['instructions'])
        embed.assert_not_awaited()

    async def test_explicit_abstention_does_not_fall_back_to_embedding(self):
        es = AsyncMock()
        es.search.return_value = {'hits': {'hits': []}}
        with patch.object(skills, 'get_es', return_value=es), patch.object(skills, 'route_local_skills', AsyncMock(return_value={
            'skills': [], 'calculations': []
        })), patch.object(skills, 'get_embedding', AsyncMock()) as embed:
            self.assertEqual(await skills.match_skills('Is this okay?'), [])
        embed.assert_not_awaited()


class RoutingContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_provider_does_not_receive_routing_request(self):
        with patch.object(skill_routing, 'get_provider_config', AsyncMock(return_value={
            'type': 'openai', 'base_url': 'https://example.com'
        })), patch.object(skill_routing.httpx, 'AsyncClient') as client:
            self.assertIsNone(await skill_routing.route_local_skills('Review code', [
                {'id': 'review', 'name': 'review', 'description': 'Review'}]))
        client.assert_not_called()

    async def test_unknown_ids_and_invalid_shapes_are_rejected(self):
        for payload in [{'skills': ['invented']}, {'skills': 'review'},
                        {'skills': ['review', 'review', 'review']}, ['review']]:
            response = MagicMock()
            response.json.return_value = {'choices': [{'message': {'content': json.dumps(payload)}}]}
            client = AsyncMock()
            client.post.return_value = response
            client.__aenter__.return_value = client
            with self.subTest(payload=payload), patch.object(skill_routing, 'get_provider_config', AsyncMock(return_value={
                'type': 'openai', 'is_local': True, 'base_url': 'http://localhost/v1', 'model': 'local'
            })), patch.object(skill_routing.httpx, 'AsyncClient', return_value=client):
                self.assertIsNone(await skill_routing.route_local_skills('Review code', [
                    {'id': 'review', 'name': 'review', 'description': 'Review'}]))
