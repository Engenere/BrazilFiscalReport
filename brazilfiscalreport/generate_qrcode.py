import qrcode


def draw_qr_code(
    self,
    qr_code_data,
    y_margin_ret,
    x_offset,
    y_offset,
    box_size=10,
    border=1,
    size=None,
):
    """
    Desenha o QR Code na página.

    `box_size` é a resolução da imagem (pixels por módulo do QR) e `size` é
    o lado impresso, em mm. Os dois eram a mesma coisa: quem pedia um QR de
    36mm gerava uma imagem com 36 pixels por módulo. `size` separa os dois
    e, quando omitido, mantém o comportamento antigo.
    """
    size = box_size if size is None else size
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(qr_code_data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img_bytes = qr_img.get_image()

    num_x = y_margin_ret + x_offset
    num_y = self.t_margin + y_offset

    self.image(qr_img_bytes, x=num_x + 1, y=num_y + 1, w=size, h=size)
