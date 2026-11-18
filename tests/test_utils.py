import unittest

from brazilfiscalreport import utils


class TestUtils(unittest.TestCase):
    def setUp(self):
        super().setUp()

    def test_format_cpf_cnpj(self):
        cpf = utils.format_cpf_cnpj("76586507812")
        self.assertEqual("765.865.078-12", cpf)

    def test_format_cnpj_alfanumerico(self):
        cnpj = utils.format_cpf_cnpj("7TTTY04J000108")
        self.assertEqual("7T.TTY.04J/0001-08", cnpj)

    def test_format_cnpj_numerico(self):
        cnpj = utils.format_cpf_cnpj("11222333000181")
        self.assertEqual("11.222.333/0001-81", cnpj)

    def test_format_cnpj_ja_formatado(self):
        cnpj = utils.format_cpf_cnpj("11.222.333/0001-81")
        self.assertEqual("11.222.333/0001-81", cnpj)

    def test_format_cnpj_alfanumerico_ja_formatado(self):
        cnpj = utils.format_cpf_cnpj("7T.TTY.04J/0001-08")
        self.assertEqual("7T.TTY.04J/0001-08", cnpj)

    def test_format_cnpj_alfanumerico_letras_minusculas(self):
        cnpj = utils.format_cpf_cnpj("xt9cdvwj000172")
        self.assertEqual("XT.9CD.VWJ/0001-72", cnpj)

    def test_format_cnpj_alfanumerico_letra_no_final(self):
        cnpj = utils.format_cpf_cnpj("12ABC34501DE35")
        self.assertEqual("12.ABC.345/01DE-35", cnpj)

    def test_format_cpf_cnpj_vazio(self):
        doc = utils.format_cpf_cnpj("")
        self.assertEqual("", doc)

    def test_format_number(self):
        number = utils.format_number("19500")
        self.assertEqual("19.500", number)

    def test_format_rate(self):
        for rate, expected in [
            ("12.0000", "12,00%"),
            ("0.1", "0,10%"),
            ("8.6625", "8,6625%"),
            ("", ""),
        ]:
            with self.subTest(rate=rate):
                self.assertEqual(expected, utils.format_rate(rate))
        self.assertEqual("8,665", utils.format_rate("8.665", suffix=""))


class TestDescribeVolumes(unittest.TestCase):
    URL = "{http://www.portalfiscal.inf.br/nfe}"

    def volumes(self, xml):
        from xml.etree import ElementTree

        transp = ElementTree.fromstring(
            f'<transp xmlns="http://www.portalfiscal.inf.br/nfe">{xml}</transp>'
        )
        return transp.findall(f"{self.URL}vol")

    def test_describe_volumes(self):
        vols = self.volumes(
            "<vol><qVol>4</qVol><esp>CAIXA</esp><marca>ACME</marca>"
            "<nVol>001</nVol><pesoL>10.500</pesoL><pesoB>12.000</pesoB></vol>"
            "<vol><qVol>10</qVol><esp>PALETE</esp><pesoB>30.000</pesoB></vol>"
            "<vol><esp>SACO</esp></vol>"
        )
        self.assertEqual(
            utils.describe_volumes(vols, self.URL),
            "4 CAIXA, marca ACME, nº 001, peso bruto 12,000, peso líquido 10,500; "
            "10 PALETE, peso bruto 30,000; SACO",
        )

    def test_describe_no_volumes(self):
        self.assertEqual(utils.describe_volumes([], self.URL), "")
