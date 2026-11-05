URL = ".//{http://www.portalfiscal.inf.br/nfe}"
DEFAULT_FIELD_HEIGHT = 6
DEFAULT_HEIGHT_FONT_CONTENT = 3
HEIGHT_FONT_BLOCK_DESC = 3
# Carrier block: one volume line per vol group, the first one with the labels
# and the next ones, shorter, with the values only. Beyond MAX_VOLUME_LINES the
# volumes are listed in the additional data instead of growing the block.
MAX_VOLUME_LINES = 5
VOLUME_LINE_HEIGHT = 3.5
# Product table: line height of the item rows (multiplied by the font size
# factor), line height of the header row and inner padding of every cell.
PRODUCT_LINE_HEIGHT = 2.5
PRODUCT_HEADER_LINE_HEIGHT = 2.2
PRODUCT_CELL_PADDING = 0.5
# QR Code box printed beside "DADOS ADICIONAIS" (NT 2026.010, item 4.5). The
# size follows the only rule published so far for the QR Code of the NF-e
# model 55 (NT 2026.003, item 3.4): 22 mm of code inside a box of at least
# 25 x 25 mm, the rest being the quiet zone.
QR_CODE_SIZE = 22
QR_CODE_BOX_SIZE = 25
QR_CODE_BLOCK_WIDTH = 26
QR_CODE_BLOCK_GAP = 2
BASE_FONT_SIZES = {
    "FONT_SIZE_DESC": 5,
    "H_FONT_DESC": 2.8,
    "FONT_SIZE_CONT": 7,
    "RECEIPT_FONT": 5,
    "PRODUCT_DESCRIPTION": 6,
    "FONT_DUPLICATES": 7,
}
