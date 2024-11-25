
import flet as ft
from typing import Callable
from pathlib import Path

class text1(ft.Row):
    def __init__(self, text1: str, text2: str,**kwargs):
        self.text1 = ft.Text(text1)
        self.text2 = ft.Text(text2)

        super().__init__([ft.Column([self.text1, self.text2])], expand=True, alignment=ft.MainAxisAlignment.START,**kwargs)

class Button1(ft.ElevatedButton):
    def __init__(self, text: str, on_click: Callable[[ft.ControlEvent], None] = None, elevation: int = 10, **kwargs):
        super().__init__(text, on_click=on_click,style=ft.ButtonStyle(color="green", padding=ft.Padding(10,10,10,10), bgcolor="darkblue", elevation=elevation, mouse_cursor=ft.MouseCursor.CLICK,shadow_color="green", side=ft.BorderRadius(100,100,100,100)),**kwargs)
        
