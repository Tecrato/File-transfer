import flet as ft
from pathlib import Path
from threading import Thread
import socket
import time
import json
import os
import sys
import asyncio
from layout.show_text import text1, Button1

# flet build apk -v --description "File transfer" --company Edouard --org com.Edouard 
# flet build apk -v --description "File transfer" --company Edouard --org com.Edouard --product "File tranfer" --build-version "1.3"

class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "File Transfer"
        self.page.adaptive = True
        self.page.window.width = 400
        self.page.window.icon = "./assets/icon.png"
        # self.page.window.wait_until_ready_to_show = True
        # self.page.window.min_height = 600
        # self.page.window.min_width = 400
        # self.page.window.skip_task_bar = True

        self.load_storage()
        
        # Variables
        self.other_device: socket.socket = None
        self.conexion_thread = Thread(target=self.__crear_conexion,daemon=True)
        self.reciving_file = False
        self.send_signal = False
        self.progreso = 0
        self.reloading_progress_bar = True
        self.disconnecting = False
        self.er_socket = None

        self.ip = self.page.client_storage.get("send_IP")
        self.port = int(self.page.client_storage.get("send_port"))


        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        
        self.ip_me = s.getsockname()[0]
        self.port_me = 1500
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Controles

        self.title = ft.Text("File Transfer",size=30,expand=True,text_align=ft.TextAlign.CENTER)

        self.Alert = ft.AlertDialog(title=ft.Text("Error"))
        self.page.overlay.append(self.Alert)
        
        self.file_picker = ft.FilePicker(on_result=self.on_path_picked)
        self.page.add(self.file_picker)

        self.send_text_ip = text1("Dirección IP: ", self.page.client_storage.get("send_IP"))
        self.send_input_ip = ft.TextField(self.page.client_storage.get("send_IP"), hint_text="Dirección IP", label="Dirección IP", visible=False)
        self.send_text_port = text1("Puerto: ", self.page.client_storage.get("send_port"))
        self.send_input_port = ft.TextField(self.page.client_storage.get("send_port"), hint_text="Puerto", label="Puerto", visible=False)
        self.send_button = Button1("Cambiar IP",on_click=self.cambiar_ip_send)

        self.sending_file_name = text1("Archivo: ", self.page.client_storage.get("file_path").replace("\\","/").split("/")[-1], height=50)
        self.sending_button_change_file = Button1("Cambiar",lambda event: self.file_picker.pick_files("Seleccione un archivo"))
        self.sending_progress_bar = ft.ProgressBar(color="green", bgcolor="aaa", value=0, height=10, expand=True)
        self.sending_button = Button1("Enviar",on_click=self.init_sending)

        self.snackbar = ft.SnackBar(ft.Text("Bienvenido a File Transfer"), open=True, duration=3000, action="Cerrar")
        self.page.overlay.append(self.snackbar)



        # ft.
        self.page.add(ft.SafeArea(ft.Column([
            ft.Row([
                self.title,
            ]),
            
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
                        ft.Text("Tu Direccion",text_align=ft.TextAlign.LEFT, expand=True),
                    ],alignment=ft.MainAxisAlignment.START),
                        
                    text1("Dirección IP: ", self.ip_me),
                    text1("Puerto: ", self.port_me),
                ], spacing=15),
                ft.Column([
                    ft.Row([
                        ft.Text("Another Direccion",text_align=ft.TextAlign.LEFT, expand=True),
                    ],alignment=ft.MainAxisAlignment.START),
                    self.send_text_ip,
                    self.send_input_ip,
                    self.send_text_port,
                    self.send_input_port,
                ], spacing=15),
            ]),
            ft.Row([
                self.send_button
            ],alignment=ft.MainAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.CENTER, scroll=True, expand=True),expand=True))
        # ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, scroll=True),expand=False, height=self.page.window.height-70))
        

        
        self.page.run_task(self.actualizar_bar_progreso)

        self.page.update()

    async def actualizar_bar_progreso(self):
        while self.reloading_progress_bar:
            self.sending_progress_bar.value = self.progreso
            self.sending_progress_bar.update()
            await asyncio.sleep(1/30)

    def load_storage(self):
        self.save_path = Path(os.path.expanduser("~/Downloads"))/"File Transfer/"
        self.save_path.mkdir(parents=True, exist_ok=True)
        if not self.page.client_storage.contains_key("carpeta_save"):
            self.page.client_storage.set("carpeta_save", "")
        if not self.page.client_storage.contains_key("send_IP"):
            self.page.client_storage.set("send_IP", "192.168.1.110")
        if not self.page.client_storage.contains_key("send_port"):
            self.page.client_storage.set("send_port", "1500")
        if not self.page.client_storage.contains_key("file_path"):
            self.page.client_storage.set("file_path", "")
        
    def cambiar_ip_send(self,event):
        self.send_input_ip.visible = True
        self.send_text_ip.visible = False
        self.send_text_port.visible = False
        self.send_input_port.visible = True
        self.send_button.text = "Confirmar"
        self.send_button.on_click = self.confirmar_cambio_ip_send
        self.page.update()

    def confirmar_cambio_ip_send(self,event):
        self.page.client_storage.set("send_IP", self.send_input_ip.value)
        self.page.client_storage.set("send_port", int(self.send_input_port.value))

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
            ...
    
        if result.files:
            self.page.client_storage.set("file_path", result.files[0].path)
            self.sending_file_name.text2.value = result.files[0].name
        self.page.update()

    def desconectar(self, event):
        self.disconnecting = True
        try:
            self.socket.close()
        except:
            pass
        try:
            self.er_socket.close()
        except:
            pass
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.title.color = "white"
        self.page.update()

    def crear_conexion(self, event=None):
        if not self.checkear_configuracion():
            return
        if self.conexion_thread.is_alive():
            self.conexion_thread.join(.5)
        self.conexion_thread = Thread(target=self.__crear_conexion,daemon=True)
        self.conexion_thread.start()

    def __crear_conexion(self):
        print("creando conexion")
        try:
        # self.socket.bind((self.ip_me, self.port_me))
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
        except Exception as err:
            print(err)
            print(type(err))
            if not self.disconnecting:
                self.Alert.title.value = "Error al recibir la conexion"
                self.Alert.open = True
                self.title.color ="red"
            else:
                self.title.color = "white"
            self.page.update()
            return

    def conectar(self, event=None):
        if not self.checkear_configuracion():
            return
        if self.conexion_thread.is_alive():
            self.conexion_thread.join(.5)
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
        except Exception as e:
            print(e)
            print(type(e))
            self.Alert.title.value = "Error al conectar"
            self.Alert.open = True
            self.title.color ="red"
            
            self.page.update()

    def socket_listener(self, mode: int = 0):
        self.er_socket = self.other_device if mode == 0 else self.socket
        self.er_socket.settimeout(10)
        self.title.color ="green"
        self.title.update()
        print("iniciando socket_listener")
        
        
        print(f"{self.er_socket}")
        while True:
            time.sleep(.5)
            if self.disconnecting:
                self.er_socket.send(b"shutdown")
                break
            ask = self.er_socket.recv(1024).decode()
            
            # if not ask:
            #     break
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
                print(detalles)
                self.snackbar.content = ft.Text(f"Recibiendo {detalles['nombre']}")
                self.snackbar.open = True
                self.snackbar.update()
                file_path: Path = Path(self.save_path)/detalles["nombre"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.remove(file_path)
                except:
                    pass
                file_path.touch(exist_ok=True)
                print("paso 2")
                self.er_socket.send(b"preparing")
                with open(file_path, "wb") as f:
                    progreso = 0
                    while self.reciving_file:
                        data = self.er_socket.recv(1024)
                        print("paso 2.5")
                        if data == b"finish" or data == b"waiting" or not data:
                            print(f"Line -> 281: {data}")
                            self.reciving_file = False
                            break
                        f.seek(progreso)
                        f.write(data)
                        progreso += len(data)
                        self.progreso = progreso/detalles["tamaño"]
                    print("paso 3")
                    f.close()
                    
                self.Alert.title.value = "Archivo recibido"
                self.Alert.open = True
                self.page.update()
                self.er_socket.send(b"waiting")
            elif ask == "ready":
                print("ready")
                self.progreso = 0
                detalles: dict = {"nombre": self.page.client_storage.get('file_path').replace("\\","/").split("/")[-1], "tamaño": Path(self.page.client_storage.get('file_path')).stat().st_size}
                self.er_socket.send(json.dumps(detalles).encode())
                print("Line -> 276: {}".format(json.dumps(detalles).encode()))
                self.er_socket.recv(1024)
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
                self.er_socket.close()
                break
                
    def init_sending(self, event):
        if self.page.client_storage.get("file_path") == "":
            self.Alert.title.value = "No se ha seleccionado ningun archivo"
            self.Alert.open = True
            return False
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

ft.app(App, "File Transfer")
