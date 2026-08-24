import datetime

import win32print


def imprimir_ticket(
    client_name,
    client_id,
    client_address,
    client_phone,
    items,
    subtotal,
    delivery_fee,
    total,
    payment_method,
    invoice_number,
):
    ancho = 48

    def dinero(valor):
        return f"${float(valor):,.2f}".replace(",", ".")

    lineas = [
        "Lady Nail Spa".center(ancho),
        "Pasto, Colombia".center(ancho),
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S").center(ancho),
        "-" * ancho,
        f"COT: {invoice_number}",
        f"Cliente: {client_name}"[:ancho],
        f"Cedula: {client_id}"[:ancho],
        f"Telefono: {client_phone}"[:ancho],
        f"Direccion: {client_address}"[:ancho],
        "-" * ancho,
        "Producto              Cant.    P.Unit       Total",
        "-" * ancho,
    ]

    for description, quantity, unit_price, item_total in items:
        nombre = description.strip().replace("\n", " ")[:20]
        lineas.append(
            f"{nombre:<20} {str(quantity):>5} {unit_price:>10,.0f} {item_total:>10,.0f}"[:ancho]
        )

    lineas.extend(
        [
            "-" * ancho,
            f"Subtotal:       {dinero(subtotal):>15}",
            f"Envio:          {dinero(delivery_fee):>15}",
            f"Total:          {dinero(total):>15}",
            f"Pago:           {payment_method}"[:ancho],
            "-" * ancho,
            "Vuelve pronto".center(ancho),
        ]
    )

    contenido = "\n".join(lineas).encode("cp858", errors="replace")
    alimentacion = b"\x1b\x64\x06"
    corte = b"\x1d\x56\x00"
    impresora = win32print.GetDefaultPrinter()
    handle = win32print.OpenPrinter(impresora)
    try:
        win32print.StartDocPrinter(handle, 1, ("Ticket de Venta", None, "RAW"))
        win32print.WritePrinter(handle, contenido)
        win32print.WritePrinter(handle, alimentacion)
        win32print.WritePrinter(handle, corte)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)
