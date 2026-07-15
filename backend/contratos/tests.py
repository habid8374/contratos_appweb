from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Administradora, Contrato


class ContratoSearchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.administradora = Administradora.objects.create(
            nombre='Administradora Test',
            nit='900123456'
        )
        self.contrato = Contrato.objects.create(
            numero_contrato='CT-001',
            administradora=self.administradora,
            modalidad=Contrato.Modalidad.EVENTO,
            objeto='Contrato de prueba',
            fecha_inicio='2024-01-01',
            fecha_fin='2026-12-31',
            valor_total='1000000.00',
            estado=Contrato.Estado.ACTIVO,
        )

    def test_search_endpoint_returns_matching_contracts(self):
        response = self.client.get(reverse('buscar-contratos'), {'q': 'test'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['numero_contrato'], 'CT-001')
        self.assertEqual(response.data[0]['administradora']['nombre'], 'Administradora Test')

    def test_detail_endpoint_returns_contract_information(self):
        response = self.client.get(reverse('detalle-contrato', args=[self.contrato.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['numero_contrato'], 'CT-001')
        self.assertEqual(response.data['administradora']['nombre'], 'Administradora Test')
