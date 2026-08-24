from PyQt5.QtWidgets import (
    QWidget,
    QMessageBox,
)
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSignal
import logging

from ..ui import Ui_Facturas
from ..database.database import SessionLocal
from ..controllers.facturas_crud import *
from ..controllers.producto_crud import *
from ..controllers.tipo_ingreso_crud import *
from ..controllers.ingresos_crud import *
from ..utils.enviar_notifi import enviar_notificacion
from ..utils.restructura_ticket import generate_ticket
from ..utils.imprimir_ticket import imprimir_ticket

logging.basicConfig(
    filename="systock.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Facturas_View(QWidget, Ui_Facturas):
    enviar_facturas_A = pyqtSignal(dict)
    enviar_facturas_B = pyqtSignal(dict)
    enviar_facturas_Credito = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(Facturas_View, self).__init__(parent)
        self.setupUi(self)

        self.InputBuscador.setPlaceholderText(
            "Buscar por ID, Cliente, Fecha, Metodo de pago o Tipo deFactura"
        )
        self.InputBuscador.textChanged.connect(self.buscar_facturas)

        self.TablaFacturas.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.TablaFacturas.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.TablaFacturas.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.TablaFacturas.setColumnWidth(0, 50)
        self.TablaFacturas.setColumnWidth(5, 120)
        self.TablaFacturas.setColumnWidth(6, 120)

        self.BtnGenerarTicket.clicked.connect(self.generar_ticket)
        self.BtnImprimirFactura.clicked.connect(self.imprimir_factura)
        self.BtnEditarFactura.clicked.connect(self.editar_factura)

    def showEvent(self, event):
        super().showEvent(event)
        self.limpiar_tabla_facturas()
        self.mostrar_facturas()
        self.InputBuscador.clear()
                        
    
    def mostrar_facturas(self):
        # Obtener datos de la tabla
        self.db = SessionLocal()
        rows = obtener_facturas(self.db)

        self.actualizar_tabla_facturas(rows)
        print("Mostrar facturas en la tabla")

        # Cerrar la conexión a la base de datos
        self.db.close()

    def limpiar_tabla_facturas(self):
        self.TablaFacturas.setRowCount(0)

    def actualizar_tabla_facturas(self, rows):
        if not rows:
            print("No hay filas para mostrar.")
            self.TablaFacturas.setRowCount(0)
            return

        try:
            self.TablaFacturas.setRowCount(0)

             # Ordenar filas por ID en orden descendente (de mayor a menor)
            rows.sort(key=lambda x: x.ID_Factura, reverse=False)
            # Iterar sobre las filas
            for row_idx, row in enumerate(rows):
                # Datos de la fila
                id_factura = str(row.ID_Factura)
                fecha = str(row.Fecha_Factura)
                fecha_conf = str(row.fecha_modificacion) if row.fecha_modificacion else "Actual"
                cliente = str(row.cliente)
                monto_efectivo = str(row.Monto_efectivo)
                monto_transaccion = str(row.Monto_TRANSACCION)
                estado = "Pagado" if row.Estado else "Pendiente"
                id_tipo_factura = str(row.tipofactura)
                id_metodo_pago = str(row.metodopago)
                usuario = str(row.usuario)
                total = row.Monto_efectivo + row.Monto_TRANSACCION
                domicilio = row.Domicilio

                self.TablaFacturas.insertRow(0)
                # Configurar items de la tabla
                items = [
                    (id_factura, 0),
                    (usuario, 1),
                    (id_metodo_pago, 2),
                    (cliente, 3),
                    (id_tipo_factura, 4),
                    (fecha, 5),
                    (fecha_conf, 6),  # Texto fijo
                    (monto_efectivo, 7),
                    (monto_transaccion, 8),
                    (str(total), 9),
                    (estado, 10),
                ]

                # Determinar color de texto
                if domicilio == True:
                    color = QtGui.QColor("green")
                else:
                    color = QtGui.QColor("black")

                # Añadir items a la tabla
                for value, col_idx in items:
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    item.setForeground(QtGui.QBrush(color))
                    self.TablaFacturas.setItem(0, col_idx, item)
                    
        except Exception as e:
            print(f"Error al mostrar las facturas: {e}")

    def obtener_ids_seleccionados(self):
        """
        Obtiene los IDs de los productos seleccionados en la tabla.
        """
        filas_seleccionadas = self.TablaFacturas.selectionModel().selectedRows()
        ids = []

        for fila in filas_seleccionadas:
            id_producto = self.TablaFacturas.item(
                fila.row(), 0
            ).text()  # Columna 0: ID del producto
            ids.append(int(id_producto))

        return ids

    def eliminar_factura(self):
        """
        Elimina una factura.
        """
        # Obtener el ID de la factura seleccionada
        ids = self.obtener_ids_seleccionados()

        if not ids:
            enviar_notificacion(
                "Advertencia", "No se seleccionaron facturas para eliminar."
            )
            return
        
        for id_factura in ids:
            facturas = obtener_factura_por_id(self.db, id_factura)
            
            if facturas.tipofactura == "Credito":
                QMessageBox.warning(self, "Factura", f"La factura {id_factura} no es una factura de venta.")
                return
            

        respuesta = QtWidgets.QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar {len(ids)} factura(s)?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if respuesta == QtWidgets.QMessageBox.Yes:
            try:
                self.db = SessionLocal()

                for id_factura in ids:
                    eliminar_factura(self.db, id_factura)

                self.db.commit()
                enviar_notificacion("Éxito", "Factura(s) eliminada(s) correctamente.")

                # Actualizar la tabla
                self.limpiar_tabla_facturas()
                self.mostrar_facturas()

            except Exception as e:
                enviar_notificacion("Error", f"Error al eliminar facturas: {e}")
            finally:
                self.db.close()

    def buscar_facturas(self):
        """
        Busca facturas en la base de datos y actualiza la tabla.
        """
        busqueda = self.InputBuscador.text().strip()
        if not busqueda:
            self.mostrar_facturas()
            return

        self.db = SessionLocal()

        facturas = buscar_facturas(self.db, busqueda)
        self.actualizar_tabla_facturas(facturas)

        self.db.close()

    def generar_ticket(self):
        """
        Genera un ticket de venta para la factura seleccionada.
        """
        ids = self.obtener_ids_seleccionados()

        if not ids:
            enviar_notificacion(
                "Advertencia", "No se seleccionaron facturas para generar ticket."
            )
            return
        for id_factura in ids:
            facturas = obtener_factura_por_id(self.db, id_factura)
            
            if facturas.tipofactura == "Credito":
                QMessageBox.warning(self, "Factura", f"La factura {id_factura} no es una factura de venta.")
                return

        db = SessionLocal()

        # Obtener la factura completa
        factura_completa = obtener_factura_completa(db, ids[0])

        if not factura_completa:
            print(f"No se encontró la factura con ID {ids[0]}")
            return
        # Extraer los datos de la factura
        factura = factura_completa["Factura"]
        cliente = factura_completa["Cliente"]  # Acceder al primer elemento de la lista
        detalles = factura_completa["Detalles"]

        # Calcular subtotal y descuento
        subtotal = sum(detalle["Subtotal"] for detalle in detalles)
        delivery_fee = factura["Descuento"]

        # Extraer información necesaria para el ticket
        client_name = f"{cliente['Nombre']} {cliente['Apellido']}"
        client_id = cliente["ID_Cliente"]
        client_address = cliente["Direccion"]
        client_phone = cliente["Teléfono"]
        items = [
            {
                "quantity": detalle["Cantidad"],
                "name": detalle.get(
                    "Producto", "Producto sin nombre"
                ),  # Asegúrate de incluir el nombre del producto en la consulta
                "unit_price": (
                    float(detalle["Precio_Unitario"])
                    if isinstance(detalle["Precio_Unitario"], (int, float))
                    else 0.0
                ),
            }
            for detalle in detalles
        ]

        items2 = []
        for item in items:
            quantity = item["quantity"]
            description = item["name"]
            value = float(item["unit_price"])

            items2.append((quantity, description, value))

        # Calcular el total
        total = subtotal - delivery_fee

        # Extraer información adicional de la factura
        payment_method = factura["MetodoPago"]
        invoice_number = factura["ID_Factura"]

        if payment_method == "Efectivo":
            pago = f"{factura['Monto_efectivo']}"
        elif payment_method == "Transferencia":
            pago = f"{factura['Monto_TRANSACCION']}"
        else:
            pago = f"{factura['Monto_efectivo']}/{factura['Monto_TRANSACCION']}"

        pan = "123456789"  # Número fijo de ejemplo, cámbialo si es necesario

        bandera = generate_ticket(
            client_name=client_name,
            client_id=client_id,
            client_address=client_address,
            client_phone=client_phone,
            items=items2,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            payment_method=payment_method,
            invoice_number=invoice_number,
            pan=pan,
            pago=pago,
            filename=None,  # Puedes cambiar esto según tu necesidad
        )

        if bandera:
            QMessageBox.warning(self, "Ticket", f"Factura generada exitosamente.")

    def imprimir_factura(self):
        ids = self.obtener_ids_seleccionados()
        if not ids:
            logger.warning("Impresion cancelada: no se selecciono una factura")
            enviar_notificacion("Advertencia", "Seleccione una factura para imprimir.")
            return

        logger.info("Solicitud de impresion para factura(s): %s", ids)
        factura_completa = obtener_factura_completa(self.db, ids[0])
        if not factura_completa:
            logger.error("No se encontro la factura seleccionada: %s", ids[0])
            QMessageBox.warning(self, "Factura", "No se encontró la factura seleccionada.")
            return

        factura = factura_completa["Factura"]
        cliente = factura_completa["Cliente"]
        detalles = factura_completa["Detalles"]
        try:
            subtotal = sum(detalle["Subtotal"] for detalle in detalles)
            delivery_fee = factura["Descuento"]
            items = [
                (
                    detalle.get("Producto", "Producto sin nombre"),
                    detalle["Cantidad"],
                    float(detalle["Precio_Unitario"]),
                    float(detalle["Subtotal"]),
                )
                for detalle in detalles
            ]
            if factura["MetodoPago"] == "Efectivo":
                pago = str(factura["Monto_efectivo"])
            elif factura["MetodoPago"] == "Transferencia":
                pago = str(factura["Monto_TRANSACCION"])
            else:
                pago = f"{factura['Monto_efectivo']}/{factura['Monto_TRANSACCION']}"

            imprimir_ticket(
                client_name=f"{cliente['Nombre']} {cliente['Apellido']}",
                client_id=cliente["ID_Cliente"],
                client_address=cliente["Direccion"],
                client_phone=cliente["Teléfono"],
                items=items,
                subtotal=float(subtotal),
                delivery_fee=float(delivery_fee),
                total=float(subtotal - delivery_fee),
                payment_method=factura["MetodoPago"],
                invoice_number=factura["ID_Factura"],
            )
            logger.info("Factura impresa correctamente: %s", factura["ID_Factura"])
            QMessageBox.information(self, "Éxito", "Factura enviada a la impresora.")
        except Exception as e:
            logger.exception("Error al imprimir factura %s", ids[0])
            QMessageBox.critical(self, "Error", f"Error al imprimir la factura: {e}")

    def editar_factura(self):
        """Abrir ventana de ventas con los datos de la factura seleccionada."""
        try:
            ids = self.obtener_ids_seleccionados()

            if not ids:
                enviar_notificacion(
                    "Advertencia", "No se seleccionaron facturas para editar."
                )
                return
            
            for id_factura in ids:
                facturas = obtener_factura_por_id(self.db, id_factura)
                
                if facturas.tipofactura == "Credito":
                    QMessageBox.warning(self, "Factura", f"La factura {id_factura} no es una factura de venta.")
                    return
            
            # Llamar a la función para obtener todos los datos de la factura
            factura_completa = obtener_factura_completa(self.db, ids[0])

            if not factura_completa:
                QMessageBox.showerror(
                    "Error", f"No se encontró la factura con ID {ids[0]}."
                )
                return

            if factura_completa["Factura"]["TipoFactura"] == "Factura A":
                self.enviar_facturas_A.emit(factura_completa)

            elif factura_completa["Factura"]["TipoFactura"] == "Factura B":
                self.enviar_facturas_B.emit(factura_completa)

            elif factura_completa["Factura"]["TipoFactura"] == "Credito":
                self.enviar_facturas_Credito.emit(factura_completa)

        except Exception as e:
            print(f"Error al abrir ventana de ventas: {e}")
