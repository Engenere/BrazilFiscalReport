import qrcode


def draw_qr_code(
    self, qr_code_data, y_margin_ret, x_offset, y_offset, box_size=10, border=1
):
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

    self.image(qr_img_bytes, x=num_x + 1, y=num_y + 1, w=box_size, h=box_size)
