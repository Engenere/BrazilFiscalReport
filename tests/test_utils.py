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


class TestSummarizeVolumes(unittest.TestCase):
    URL = "{http://www.portalfiscal.inf.br/nfe}"

    def volumes(self, xml):
        from xml.etree import ElementTree

        transp = ElementTree.fromstring(
            f'<transp xmlns="http://www.portalfiscal.inf.br/nfe">{xml}</transp>'
        )
        return transp.findall(f"{self.URL}vol")

    def test_single_volume_is_kept_as_is(self):
        vols = self.volumes(
            "<vol><qVol>4</qVol><esp>CAIXA</esp><marca>ACME</marca>"
            "<nVol>001</nVol><pesoL>10.500</pesoL><pesoB>12.000</pesoB></vol>"
        )
        summary = utils.summarize_volumes(vols, self.URL)
        self.assertEqual(
            summary,
            utils.VolumesSummary("4", "CAIXA", "ACME", "001", "12.000", "10.500"),
        )

    def test_several_volumes_are_summed(self):
        vols = self.volumes(
            "<vol><qVol>4</qVol><esp>CAIXA</esp><pesoL>10.500</pesoL>"
            "<pesoB>12.000</pesoB></vol>"
            "<vol><qVol>10</qVol><esp>PALETE</esp><pesoL>26.000</pesoL>"
            "<pesoB>30.000</pesoB></vol>"
            "<vol><qVol>18</qVol><esp>SACO</esp><pesoL>48.000</pesoL>"
            "<pesoB>54.000</pesoB></vol>"
        )
        summary = utils.summarize_volumes(vols, self.URL)
        self.assertEqual(summary.q_vol, "32")
        self.assertEqual(summary.esp, "CAIXA, PALETE, SACO")
        self.assertEqual(summary.marca, "")
        self.assertEqual(summary.n_vol, "")
        self.assertEqual(summary.peso_b, "96.000")
        self.assertEqual(summary.peso_l, "84.500")

    def test_repeated_values_are_listed_once(self):
        vols = self.volumes(
            "<vol><qVol>1</qVol><esp>CAIXA</esp><marca>ACME</marca></vol>"
            "<vol><qVol>2</qVol><esp>CAIXA</esp><marca>ACME</marca></vol>"
        )
        summary = utils.summarize_volumes(vols, self.URL)
        self.assertEqual(summary.q_vol, "3")
        self.assertEqual(summary.esp, "CAIXA")
        self.assertEqual(summary.marca, "ACME")

    def test_missing_amounts_stay_empty(self):
        vols = self.volumes("<vol><esp>CAIXA</esp></vol><vol><qVol>2</qVol></vol>")
        summary = utils.summarize_volumes(vols, self.URL)
        self.assertEqual(summary.q_vol, "2")
        self.assertEqual(summary.peso_b, "")
        self.assertEqual(summary.peso_l, "")

    def test_without_volumes(self):
        summary = utils.summarize_volumes([], self.URL)
        self.assertFalse(any(summary))
