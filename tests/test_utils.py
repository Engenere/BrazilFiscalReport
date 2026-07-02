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
