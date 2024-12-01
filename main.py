import flet as ft
from pathlib import Path
from threading import Thread
import socket
import time
import json
import os
import asyncio
import re
from layout.show_text import text1, Button1


# flet build apk -v --build-version "1.3" --skip-flutter-doctor
# flet build windows -v --build-version "1.3" --cleanup-on-compile --skip-flutter-doctor

# no usar --clear-cache

# print(os.getenv("FLET_APP_STORAGE_DATA"))
# print(os.getenv("FLET_APP_STORAGE_TEMP"))

def format_size_bits_to_bytes(size) -> list:
    count = 0
    while size > 1024:
        size /= 1024
        count += 1
    return f"{size:.2f}{UNIDADES_BYTES[count]}"

UNIDADES_BYTES = {
    0: 'B',
    1: 'KB',
    2: 'MB',
    3: 'GB',
    4: 'TB',
    5: 'PB',
    6: 'EB',
    7: 'ZB',
    8: 'YB'
}

class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "File Transfer"
        self.page.window.width = 400
        self.page.window.icon = "./assets/icon.png"
        self.page.window.min_height = 600
        self.page.window.min_width = 400
        self.page.window.prevent_close = True
        self.page.window.on_event = self.window_event
        # self.page.window.wait_until_ready_to_show = True

        self.load_storage()
        
        # Variables
        self.other_device: socket.socket = None
        self.conexion_thread = Thread(target=self.__crear_conexion,daemon=True)
        self.reciving_file = False
        self.reciving_file_path_file = None
        self.send_signal = False
        self.progreso = 0
        self.disconnecting = False
        self.er_socket = None
        self.running = True

        self.ip = self.page.client_storage.get("send_IP")
        self.port = int(self.page.client_storage.get("send_port"))

        # self.ip = "192.168.0.103"
        # self.port = 1500


        self.ip_me = "127.0.0.1"
        self.port_me = 1500
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Controles

        self.title = ft.Text("File Transfer",size=30,text_align=ft.TextAlign.CENTER)

        self.Alert = ft.AlertDialog(title=ft.Text("Bienvenido"))
        self.Alert.actions.append(ft.TextButton("OK", on_click=self.cerrar_alert))
        self.page.overlay.append(self.Alert)

        self.snackbar = ft.SnackBar(content=ft.Text("Preparando"))
        self.page.overlay.append(self.snackbar)
        
        self.file_picker = ft.FilePicker(on_result=self.on_path_picked)
        self.page.add(self.file_picker)

        self.my_ip_text = text1("Dirección IP: ", self.ip_me)

        self.send_text_ip = text1("Dirección IP: ", self.page.client_storage.get("send_IP"))
        self.send_input_ip = ft.TextField(self.page.client_storage.get("send_IP"), hint_text="Dirección IP", label="Dirección IP", visible=False)
        self.send_text_port = text1("Puerto: ", self.page.client_storage.get("send_port"))
        self.send_input_port = ft.TextField(self.page.client_storage.get("send_port"), hint_text="Puerto", label="Puerto", visible=False)
        self.send_button = Button1("Cambiar IP",on_click=self.cambiar_ip_send)

        self.sending_file_name = text1("Archivo: ", self.page.client_storage.get("file_path").replace("\\","/").split("/")[-1], height=50)
        self.sending_button_change_file = Button1("Cambiar Archivo",lambda event: self.file_picker.pick_files("Seleccione un archivo"))
        self.sending_progress_bar = ft.ProgressBar(color="green", bgcolor="aaa", value=0, height=10, expand=True)
        self.sending_button = Button1("Enviar",on_click=self.init_sending)

        self.page.add(
            ft.AppBar(title=self.title,elevation=0, center_title=True,actions=[ft.IconButton(icon=ft.Icons.INFO, on_click=self.info)]),
        )

        self.page.add(ft.SafeArea(ft.Column([
            ft.Column([
                ft.Row([
                    Button1("conectar",width=120,height=120,elevation=10,on_click=self.conectar),
                    Button1("Crear conexion",width=120,height=120,elevation=10,on_click=self.crear_conexion),
                ],expand=True,alignment=ft.MainAxisAlignment.SPACE_AROUND),
                ft.Row([
                    Button1("Desconectar",elevation=10,on_click=self.desconectar),
                ],expand=True,alignment=ft.MainAxisAlignment.SPACE_AROUND),
            ]),
            ft.Divider(),
            ft.Row([
                ft.Text("Enviar archivo", size=30,expand=True,text_align=ft.TextAlign.CENTER),
            ]),
            ft.Row([
                ft.Column([
                    self.sending_file_name,
                    ft.Row([
                        self.sending_button_change_file,
                        self.sending_button,
                    ],expand=True,alignment=ft.MainAxisAlignment.SPACE_AROUND),
                    ft.Row([
                        self.sending_progress_bar
                    ],expand=True,alignment=ft.MainAxisAlignment.CENTER, height=30),
                ], expand=True, alignment=ft.MainAxisAlignment.SPACE_AROUND),
            ], expand=True),
            ft.Divider(),
            ft.Row([
                ft.Text("Configuración", size=30,expand=True,text_align=ft.TextAlign.CENTER),
            ], spacing=10),
            ft.Row([
                ft.Column([
                    ft.Row([
                        ft.Text("Tu Direccion",text_align=ft.TextAlign.CENTER, expand=True),
                    ],alignment=ft.MainAxisAlignment.START),
                        
                    self.my_ip_text,
                    text1("Puerto: ", self.port_me),
                ], spacing=15, expand=True),
                ft.VerticalDivider(),
                ft.Column([
                    ft.Row([
                        ft.Text("otra Direccion",text_align=ft.TextAlign.CENTER, expand=True),
                    ],alignment=ft.MainAxisAlignment.START),
                    self.send_text_ip,
                    self.send_input_ip,
                    self.send_text_port,
                    self.send_input_port,
                ], spacing=15, expand=True),
            ], expand=True),
            ft.Row([
                ft.ElevatedButton("Cambiar Carpeta guardado",on_click=lambda e: self.file_picker.get_directory_path()),
                self.send_button
            ],alignment=ft.MainAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND, scroll=False, expand=True),expand=True))
        

        self.page.update()
        self.page.run_task(self.actualizar_bar_progreso)
        self.page.run_task(self.actualizar_ip_me)

        if self.page.client_storage.get("tutorial") == False:
            self.tutorial()

    def window_event(self, e: ft.WindowEvent):
        if e.type == ft.WindowEventType.CLOSE:
            if self.reciving_file:
                self.reciving_file = False
                time.sleep(1)
                try:
                    os.remove(self.reciving_file_path_file)
                except:
                    pass
                self.send_signal = False
                self.progreso = 0
            self.page.window.close()
            self.page.window.destroy()
        elif e.type == ft.WindowEventType.MAXIMIZE:
            self.page.window.maximize()
        elif e.type == ft.WindowEventType.MINIMIZE:
            self.page.window.minimize()

    async def actualizar_ip_me(self):
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                self.ip_me = s.getsockname()[0]
            except Exception as e:
                self.ip_me = socket.gethostbyname(socket.gethostname())
            except Exception as e:
                self.Alert.title.value = "Error al obtener la direccion IP\n{}".format(e)
                self.Alert.open = True
            finally:
                self.my_ip_text.text2.value = self.ip_me
                self.page.update()
            await asyncio.sleep(1)

    async def actualizar_bar_progreso(self):
        while self.running:
            self.sending_progress_bar.value = self.progreso
            self.sending_progress_bar.update()
            await asyncio.sleep(1/30)

    def load_storage(self):
        # self.save_path = Path(os.path.expanduser("~/Downloads"))/"File Transfer/"
        # self.save_path.mkdir(parents=True, exist_ok=True)
        if not self.page.client_storage.contains_key("carpeta_save"):
            self.page.client_storage.set("carpeta_save", "")
        if not self.page.client_storage.contains_key("send_IP"):
            self.page.client_storage.set("send_IP", "192.168.1.110")
        if not self.page.client_storage.contains_key("send_port"):
            self.page.client_storage.set("send_port", "1500")
        if not self.page.client_storage.contains_key("file_path"):
            self.page.client_storage.set("file_path", "")
        if not self.page.client_storage.contains_key("tutorial"):
            self.page.client_storage.set("tutorial", False)
        
    def cambiar_ip_send(self,event):
        self.send_input_ip.visible = True
        self.send_text_ip.visible = False
        self.send_text_port.visible = False
        self.send_input_port.visible = True
        self.send_button.text = "Confirmar"
        self.send_button.on_click = self.confirmar_cambio_ip_send
        self.page.update()

    def confirmar_cambio_ip_send(self,event):
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", self.send_input_ip.value):
            self.Alert.title.value = "Dirección IP no válida"
            self.Alert.open = True
            self.page.update()
            return
        if not re.match(r"^\d{1,5}$", str(self.send_input_port.value)):
            self.Alert.title.value = "Puerto no válido"
            self.Alert.open = True
            self.page.update()
            return

        self.page.client_storage.set("send_port", int(self.send_input_port.value))
        self.page.client_storage.set("send_IP", self.send_input_ip.value)

        self.ip = self.page.client_storage.get("send_IP")
        self.port = int(self.page.client_storage.get("send_port"))

        self.send_text_ip.text2.value = self.send_input_ip.value
        self.send_text_port.text2.value = self.send_input_port.value
        self.send_input_ip.visible = False
        self.send_input_port.visible = False
        self.send_text_ip.visible = True
        self.send_text_port.visible = True
        self.send_button.text = "Cambiar"
        self.send_button.on_click = self.cambiar_ip_send
        self.page.update()

    def on_path_picked(self, result: ft.FilePickerResultEvent):
        if result.path: # Para cuando se selecciona una carpeta
            self.page.client_storage.set("carpeta_save", result.path)
        if result.files:
            self.page.client_storage.set("file_path", result.files[0].path)
            self.sending_file_name.text2.value = result.files[0].name
        self.page.update()

    def desconectar(self, event):
        self.disconnecting = True
        print("desconectando")
        try:
            self.conexion_thread.join(1)
            self.conexion_thread = None
        except:
            pass
        try:
            self.socket.close()
            self.socket = None
        except:
            pass
        try:
            self.er_socket.close()
            self.er_socket = None
        except Exception as e:
            pass
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.title.color = None
        self.page.update()

    def crear_conexion(self, event=None):
        if not self.checkear_configuracion():
            return
        try:
            if self.conexion_thread.is_alive():
                self.conexion_thread.join(.5)
        except:
            pass
        self.conexion_thread = Thread(target=self.__crear_conexion,daemon=True)
        self.conexion_thread.start()

    def __crear_conexion(self):
        print("creando conexion")
        try:
            try:
                self.socket.close()
            except:
                pass
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(("0.0.0.0", 1500))
            self.socket.listen(1)
            self.title.color = "yellow"
            self.title.update()
            self.other_device, address = self.socket.accept()
            self.socket_listener(0)
            print(address)
        except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError) as e:
            print("Line 280 crear conexion -> "+ str(e))
            self.Alert.title.value = "El dispositivo se ha desconectado"
            self.Alert.open = True
            self.title.color = None
            
            self.page.update()
        except Exception as err:
            print(err)
            print(type(err))
            if not self.disconnecting:
                self.Alert.title.value = "Error al recibir la conexion"
                self.Alert.open = True
                self.title.color ="red"
            else:
                self.title.color = None
            self.page.update()
            return
        finally:
            print("Terminado crear conexion")
            print(self.reciving_file)
            if self.reciving_file:
                self.reciving_file = False
                try:
                    os.remove(self.reciving_file_path_file)
                except:
                    pass
                self.send_signal = False
                
            self.progreso = 0

    def conectar(self, event=None):
        if not self.checkear_configuracion():
            return
        try:
            if self.conexion_thread.is_alive():
                self.conexion_thread.join(.5)
        except:
            pass
        self.conexion_thread = Thread(target=self.__conectar,daemon=True)
        self.conexion_thread.start()
    
    def __conectar(self):
        try:
            try:
                self.socket.close()
            except:
                pass
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.ip, int(self.port)))
            self.socket.send(b"waiting")
            self.socket_listener(1)
            print("Terminado")
        except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError) as e:
            print("Line 280 conctar -> "+ str(e))
            self.Alert.title.value = "El dispositivo se ha desconectado"
            self.Alert.open = True
            self.title.color = None
            
            self.page.update()
        except Exception as e:
            print("Line 287 -> "+ str(e) + " " + str(type(e)))
            self.Alert.title.value = "Error al conectar"
            self.Alert.open = True
            self.title.color ="red"
            
            self.page.update()
        finally:
            if self.reciving_file:
                self.reciving_file = False
                try:
                    os.remove(self.reciving_file_path_file)
                except:
                    pass
                self.send_signal = False
            self.progreso = 0

    def socket_listener(self, mode: int = 0):
        self.er_socket = self.other_device if mode == 0 else self.socket
        self.er_socket.settimeout(10)
        self.title.color ="green"
        self.title.update()
        self.reciving_file = False
        self.send_signal = False
        print("iniciando socket_listener")
        
        
        print(f"{self.er_socket}")
        while True:
            time.sleep(.5)
            if self.disconnecting:
                self.er_socket.send(b"shutdown")
                self.er_socket.close()
                self.er_socket = None
                self.disconnecting = False
                self.title.color = "white"
                self.title.update()
                return
            asd = self.er_socket.recv(1024)
            print(asd)
            ask = asd.decode()
            print("308 -> "+ ask)
            
            if ask in ["waiting", "finish"]:
                print("waiting")
                if self.send_signal:
                    self.er_socket.send(b"preparing")
                else:
                    self.er_socket.send(b"waiting")
                print("waiting 2")
            elif ask == "preparing":
                print("preparing")
                self.progreso = 0
                self.er_socket.send(b"ready")
                self.reciving_file = True
                detalles: dict = json.loads(self.er_socket.recv(1024).decode())
                if Path(Path(self.page.client_storage.get("carpeta_save"))/detalles["nombre"]).exists():
                    self.Alert.title.value = "El archivo ya existe"
                    self.Alert.open = True
                    self.page.update()
                    self.reciving_file = False
                    self.send_signal = False
                    self.er_socket.send(b"waiting")
                    continue
                print(detalles)
                self.snackbar.content = ft.Text(f"Recibiendo {detalles['nombre']} - {format_size_bits_to_bytes(detalles['tamaño'])}")
                self.snackbar.open = True
                self.snackbar.update()
                file_path: Path = Path(Path(self.page.client_storage.get("carpeta_save")))/detalles["nombre"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                # try:
                #     os.remove(file_path)
                # except:
                #     pass
                file_path.touch(exist_ok=True)
                self.reciving_file_path_file = file_path
                print("paso 2")
                self.er_socket.send(b"preparing")
                with open(file_path, "wb") as f:
                    progreso = 0
                    while self.reciving_file:
                        data = self.er_socket.recv(1024*8)
                        if data == b"finish" or data == b"waiting" or not data:
                            self.reciving_file = False
                            break
                        f.seek(progreso)
                        f.write(data)
                        progreso += len(data)
                        self.progreso = progreso/detalles["tamaño"]
                    print("paso 3")
                    f.close()
                    
                if os.stat(file_path).st_size != detalles["tamaño"]:
                    self.snackbar.content = ft.Text("Error al recibir el archivo")
                    self.snackbar.open = True
                    self.snackbar.update()
                    self.reciving_file = False
                    self.send_signal = False
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    self.er_socket.send(b"waiting")
                    continue
                self.Alert.title.value = "Archivo recibido"
                self.Alert.open = True
                self.sending_progress_bar.value = 0
                self.page.update()
                self.er_socket.send(b"waiting")
                self.reciving_file = False
            elif ask == "ready":
                print("ready")
                self.progreso = 0
                detalles: dict = {"nombre": self.page.client_storage.get('file_path').replace("\\","/").split("/")[-1], "tamaño": Path(self.page.client_storage.get('file_path')).stat().st_size}
                self.er_socket.send(json.dumps(detalles).encode())
                print("Line -> 358: {}".format(json.dumps(detalles).encode()))
                respuesta = self.er_socket.recv(1024).decode()
                print(respuesta)
                if respuesta == "waiting":
                    self.er_socket.send(b"waiting")
                    self.send_signal = False
                    continue
                progreso = 0
                with open(self.page.client_storage.get('file_path'), "rb") as f:
                    while True:
                        f.seek(progreso)
                        data = f.read(1024)
                        if not data:
                            break
                        self.er_socket.send(data)
                        progreso += len(data)
                        self.progreso = progreso/detalles["tamaño"]
                    f.close()
                    time.sleep(1)
                print("paso tercero")
                self.er_socket.send(b"finish")
                self.send_signal = False
                self.title.color = "green"
                print("fin del socket_listener")
            elif ask == "shutdown":
                raise ConnectionAbortedError()
            else:
                raise ConnectionAbortedError()
                
    def init_sending(self, event):
        if self.page.client_storage.get("file_path") == "":
            self.Alert.title.value = "No se ha seleccionado ningun archivo"
            self.Alert.open = True
            return False
        if self.page.client_storage.get("carpeta_save") == "":
            self.Alert.title.value = "No se ha seleccionado ninguna carpeta de guardado"
            self.Alert.open = True
            return False
        self.page.update()
        self.send_signal = True


    def checkear_configuracion(self):
        if self.page.client_storage.get("send_IP") == "":
            self.Alert.title.value = "No se ha configurado la direccion IP"
            self.Alert.open = True
            return False
        if self.page.client_storage.get("send_port") == "":
            self.Alert.title.value = "No se ha configurado el puerto"
            self.Alert.open = True
            return False
        return True

    def tutorial(self):
        self.page.client_storage.set("tutorial", True)
        self.Alert.title.value = "Tutorial"
        self.Alert.content = ft.Text("Bienvenido a File Transfer\n\nPara empezar a transferir archivos, debes configurar la direccion IP y el puerto del otro dispositivo.\n\nPara hacerlo, haz click en el boton 'Cambiar IP' y luego en 'Confirmar'.\n\nLuego de hacer esto debe seleccionar la carpeta que contendra los archivos recibidos.\n\nFinalmente para enviar un archivo, click en cambiar archivo y click en el boton enviar\n\nGracias por usar File Transfer")
        self.Alert.open = True
        self.Alert.on_dismiss = self.del_alert_content
        self.page.update()
    
    def del_alert_content(self,e):
        self.Alert.content = None
        self.page.update()
    def cerrar_alert(self,e):
        self.Alert.open = False
        self.page.update()
    def info(self,e):
        self.Alert.title.value = "Info"
        self.Alert.content = ft.Text(\
            "File Transfer es un programa que permite transferir archivos entre dos dispositivos conectados a la misma red.\
            \n\n\
Para empezar a transferir archivos, debes configurar la direccion IP y el puerto del otro dispositivo.\
            \n\n\
Para hacerlo, haz click en el boton 'Cambiar IP' y luego en 'Confirmar'.\
            \n\n\
Luego de hacer esto debe seleccionar la carpeta que contendra los archivos recibidos.\
            \n\n\
Finalmente para enviar un archivo, click en cambiar archivo y click en el boton enviar\
            \n\n\
Creado por Edouard Sandoval")
        self.Alert.open = True
        self.Alert.on_dismiss = self.del_alert_content
        self.page.update()

ft.app(App, "File Transfer")
