"""
OLED & TFT Converter — Дисплеи, Часы и Сенсорные экраны
Конвертер видео, GIF и изображений в формат битмапов для микроконтроллеров Arduino / ESP.
Поддерживает монохромные OLED (SSD1306, SH1106), круглые смарт-часы (GC9A01, CST816)
и цветные дисплеи TFT/IPS (ST7789, ILI9341, ST7735).
"""

import os
import sys
import time
import tempfile
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np

try:
    import cv2
    from PIL import Image, ImageOps, ImageEnhance, ImageTk, ImageSequence, ImageDraw
except ImportError:
    print("Требуются библиотеки opencv-python, Pillow и numpy.")
    sys.exit(1)


def get_base_dir():
    """Возвращает директорию, где лежит исполняемый файл или скрипт."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_ffmpeg_exe():
    """Находит ffmpeg.exe в упакованном bundle, imageio_ffmpeg или системе."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_dir = getattr(sys, '_MEIPASS')
        p1 = os.path.join(bundle_dir, 'ffmpeg.exe')
        if os.path.isfile(p1):
            return p1
        bin_dir = os.path.join(bundle_dir, 'imageio_ffmpeg', 'binaries')
        if os.path.isdir(bin_dir):
            for f in os.listdir(bin_dir):
                if f.startswith('ffmpeg') and f.endswith('.exe'):
                    return os.path.join(bin_dir, f)
    base = get_base_dir()
    p_local = os.path.join(base, 'ffmpeg.exe')
    if os.path.isfile(p_local):
        return p_local
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    import shutil
    sys_exe = shutil.which('ffmpeg')
    if sys_exe:
        return sys_exe
    return None


FFMPEG_EXE = get_ffmpeg_exe()

DISPLAY_PROFILES = {
    'SSD1306 / SH1106 128x64 (0.96" / 1.3" OLED)': {
        'width': 128, 'height': 64, 'shape': 'rect', 'depth': '1bit',
        'category': 'Монохромный OLED',
        'desc': '0.96" / 1.3" монохромный OLED (128x64, 1-бит)'
    },
    'SSD1306 128x32 (Узкий OLED 0.91")': {
        'width': 128, 'height': 32, 'shape': 'rect', 'depth': '1bit',
        'category': 'Монохромный OLED',
        'desc': '0.91" узкий монохромный дисплей (128x32, 1-бит)'
    },
    'SSD1309 / SSD1327 96x96 (Квадратный OLED)': {
        'width': 96, 'height': 96, 'shape': 'rect', 'depth': '1bit',
        'category': 'Монохромный OLED',
        'desc': '1.1" квадратный монохромный OLED (96x96)'
    },
    'SSD1306 64x48 (Wemos D1 Shield)': {
        'width': 64, 'height': 48, 'shape': 'rect', 'depth': '1bit',
        'category': 'Монохромный OLED',
        'desc': '0.66" мини-дисплей для Wemos D1 mini (64x48)'
    },
    'Круглый 1.28" OLED 128x128': {
        'width': 128, 'height': 128, 'shape': 'round', 'depth': '1bit',
        'category': 'Монохромный OLED',
        'desc': 'Круглый монохромный циферблат (128x128, 1-бит)'
    },
    'GC9A01 240x240 Круглый (1.28" Round Watch IPS)': {
        'width': 240, 'height': 240, 'shape': 'round', 'depth': 'rgb565',
        'category': 'Круглые смарт-часы',
        'desc': 'Самый популярный экран для умных часов ESP32 / RP2040 (240x240)'
    },
    'CST816 Touch Round 240x240 (Сенсорные часы)': {
        'width': 240, 'height': 240, 'shape': 'round', 'depth': 'rgb565',
        'category': 'Круглые смарт-часы',
        'desc': 'Круглый дисплей с ёмкостным сенсором тача CST816 (240x240)'
    },
    'Круглый 280x280 (1.39" Smartwatch)': {
        'width': 280, 'height': 280, 'shape': 'round', 'depth': 'rgb565',
        'category': 'Круглые смарт-часы',
        'desc': 'Круглые смарт-часы среднего размера (280x280 RGB565)'
    },
    'Круглый 360x360 (Hi-Res Round Watch)': {
        'width': 360, 'height': 360, 'shape': 'round', 'depth': 'rgb565',
        'category': 'Круглые смарт-часы',
        'desc': 'Высокое разрешение для круглых циферблатов (360x360)'
    },
    'Круглый 466x466 (AMOLED Smartwatch)': {
        'width': 466, 'height': 466, 'shape': 'round', 'depth': 'rgb565',
        'category': 'Круглые смарт-часы',
        'desc': 'Премиум AMOLED круглый экран для ESP32-S3 (466x466)'
    },
    'ST7789 240x240 (1.3" / 1.54" IPS)': {
        'width': 240, 'height': 240, 'shape': 'rect', 'depth': 'rgb565',
        'category': 'Цветные TFT/IPS',
        'desc': 'Яркий квадратный IPS экран с широкими углами обзора'
    },
    'ST7789 135x240 (LilyGO TTGO T-Display)': {
        'width': 135, 'height': 240, 'shape': 'rect', 'depth': 'rgb565',
        'category': 'Цветные TFT/IPS',
        'desc': 'Популярная плата разработчика ESP32 со встроенным дисплеем'
    },
    'ST7789 240x280 (1.69" Сенсорные часы с фаской)': {
        'width': 240, 'height': 280, 'shape': 'rect', 'depth': 'rgb565',
        'category': 'Цветные TFT/IPS',
        'desc': 'Прямоугольный экран умных часов с закруглёнными углами'
    },
    'ST7789 / ILI9341 240x320 (2.4" / 2.8" / 3.2" Touch)': {
        'width': 240, 'height': 320, 'shape': 'rect', 'depth': 'rgb565',
        'category': 'Цветные TFT/IPS',
        'desc': 'Классический дисплей с резистивным/ёмкостным тачем'
    },
    'ST7735 128x160 (1.8" TFT)': {
        'width': 128, 'height': 160, 'shape': 'rect', 'depth': 'rgb565',
        'category': 'Цветные TFT/IPS',
        'desc': 'Доступный цветной дисплей 1.8" (128x160 RGB565)'
    },
    'ST7735 128x128 (1.44" TFT)': {
        'width': 128, 'height': 128, 'shape': 'rect', 'depth': 'rgb565',
        'category': 'Цветные TFT/IPS',
        'desc': 'Миниатюрный квадратный цветной экран (128x128)'
    },
    'ILI9488 320x480 (3.5" IPS Touch)': {
        'width': 320, 'height': 480, 'shape': 'rect', 'depth': 'rgb565',
        'category': 'Цветные TFT/IPS',
        'desc': 'Большой сенсорный экран 3.5" для дашбордов и игр'
    },
    'Пользовательский (Свой размер...)': {
        'width': 128, 'height': 64, 'shape': 'rect', 'depth': '1bit',
        'category': 'Пользовательский',
        'desc': 'Задайте собственные параметры экрана выше.'
    }
}


class OledConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title('OLED & TFT Converter — Дисплеи, Часы и Сенсорные экраны')
        self.root.geometry('880x580')
        self.root.minsize(840, 540)

        self.input_file = ''
        self.src_fps = 30.0
        self.total_frames = 0
        self.duration = 0.0
        self.has_audio = False

        self.preview_cap = None
        self.gif_frames = []
        self.gif_idx = 0
        self.is_video = False
        self.is_gif = False
        self.is_playing = False
        self.play_timer = None
        self.single_image = None
        self.current_raw_frame = None  # Текущий необработанный кадр для мгновенного обновления
        self.tk_preview = None

        self.temp_wav = os.path.join(tempfile.gettempdir(), '_oled_conv_audio.wav')
        self.audio_playing = False

        self.create_ui()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    def create_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), foreground='#ffffff', background='#007acc')

        content = ttk.Frame(self.root, padding='10')
        content.pack(fill=tk.BOTH, expand=True)

        left_col = ttk.Frame(content)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # 1. Дисплей устройства
        disp_box = ttk.LabelFrame(left_col, text=' 1. Дисплей устройства ', padding='6')
        disp_box.pack(fill=tk.X, pady=(0, 4))

        self.var_profile = tk.StringVar(value=list(DISPLAY_PROFILES.keys())[0])
        self.cb_profile = ttk.Combobox(
            disp_box, textvariable=self.var_profile, state='readonly',
            values=list(DISPLAY_PROFILES.keys())
        )
        self.cb_profile.pack(fill=tk.X, padx=4, pady=2)
        self.cb_profile.bind('<<ComboboxSelected>>', self.on_profile_change)

        self.lbl_profile_desc = ttk.Label(disp_box, text='', font=('Segoe UI', 8), foreground='#0066cc')
        self.lbl_profile_desc.pack(anchor=tk.W, padx=4)

        # Фрейм для пользовательского дисплея
        self.f_custom = ttk.Frame(disp_box)
        ttk.Label(self.f_custom, text='Ш:').pack(side=tk.LEFT)
        self.var_custom_w = tk.StringVar(value='128')
        ttk.Entry(self.f_custom, textvariable=self.var_custom_w, width=5).pack(side=tk.LEFT, padx=(0, 4))
        self.var_custom_w.trace_add('write', lambda *args: self.update_canvas_size())

        ttk.Label(self.f_custom, text='В:').pack(side=tk.LEFT)
        self.var_custom_h = tk.StringVar(value='64')
        ttk.Entry(self.f_custom, textvariable=self.var_custom_h, width=5).pack(side=tk.LEFT, padx=(0, 4))
        self.var_custom_h.trace_add('write', lambda *args: self.update_canvas_size())

        self.var_custom_shape = tk.StringVar(value='rect')
        ttk.Radiobutton(self.f_custom, text='Прямоуг.', variable=self.var_custom_shape, value='rect', command=self.update_canvas_size).pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(self.f_custom, text='Круглый', variable=self.var_custom_shape, value='round', command=self.update_canvas_size).pack(side=tk.LEFT, padx=3)

        self.var_custom_depth = tk.StringVar(value='1bit')
        ttk.Radiobutton(self.f_custom, text='1-бит', variable=self.var_custom_depth, value='1bit', command=self.update_canvas_size).pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(self.f_custom, text='RGB565', variable=self.var_custom_depth, value='rgb565', command=self.update_canvas_size).pack(side=tk.LEFT, padx=3)

        # 2. Исходный файл
        file_box = ttk.LabelFrame(left_col, text=' 2. Исходный файл ', padding='6')
        file_box.pack(fill=tk.X, pady=(0, 4))

        f_row = ttk.Frame(file_box)
        f_row.pack(fill=tk.X)
        self.lbl_filename = ttk.Label(f_row, text='Файл не выбран', font=('Segoe UI', 9, 'italic'), foreground='#666')
        self.lbl_filename.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_browse = ttk.Button(f_row, text='Обзор...', width=10, command=self.browse_file)
        btn_browse.pack(side=tk.RIGHT)

        self.lbl_info = ttk.Label(file_box, text='', font=('Segoe UI', 8), foreground='#333')
        self.lbl_info.pack(anchor=tk.W, padx=2, pady=(2, 0))

        # 3. Параметры видео и цвета
        cfg_box = ttk.LabelFrame(left_col, text=' 3. Параметры видео и цвета ', padding='6')
        cfg_box.pack(fill=tk.X, pady=(0, 4))

        r_scale = ttk.Frame(cfg_box)
        r_scale.pack(fill=tk.X, pady=1)
        ttk.Label(r_scale, text='Масштаб:', width=11).pack(side=tk.LEFT)
        self.var_scale = tk.StringVar(value='fit')
        ttk.Radiobutton(
            r_scale, text='Заполнить (Crop)', variable=self.var_scale, value='fit',
            command=self.refresh_preview
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            r_scale, text='Вписать (Letterbox)', variable=self.var_scale, value='pad',
            command=self.refresh_preview
        ).pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(r_scale, text='FPS:', width=5).pack(side=tk.LEFT, padx=(10, 2))
        self.var_fps = tk.StringVar(value='auto')
        cb_fps = ttk.Combobox(
            r_scale, textvariable=self.var_fps, state='readonly', width=8,
            values=('auto', '10 FPS', '12 FPS', '15 FPS', '20 FPS', '24 FPS', '30 FPS', '60 FPS')
        )
        cb_fps.pack(side=tk.LEFT)
        cb_fps.bind('<<ComboboxSelected>>', self.on_fps_change)

        r_adj = ttk.Frame(cfg_box)
        r_adj.pack(fill=tk.X, pady=1)
        ttk.Label(r_adj, text='Контраст:', width=11).pack(side=tk.LEFT)
        self.var_contrast = tk.DoubleVar(value=1.3)
        sc_c = ttk.Scale(
            r_adj, from_=0.5, to=2.5, variable=self.var_contrast, orient=tk.HORIZONTAL,
            command=self.on_contrast_change
        )
        sc_c.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lbl_contrast_val = ttk.Label(r_adj, text='1.3x', width=5)
        self.lbl_contrast_val.pack(side=tk.LEFT, padx=(2, 0))

        ttk.Label(r_adj, text='Яркость:', width=8).pack(side=tk.LEFT, padx=(8, 2))
        self.var_brightness = tk.DoubleVar(value=1.0)
        sc_b = ttk.Scale(
            r_adj, from_=0.5, to=2.0, variable=self.var_brightness, orient=tk.HORIZONTAL,
            command=self.on_brightness_change
        )
        sc_b.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lbl_bright_val = ttk.Label(r_adj, text='1.0x', width=5)
        self.lbl_bright_val.pack(side=tk.LEFT, padx=(2, 0))

        r_misc = ttk.Frame(cfg_box)
        r_misc.pack(fill=tk.X, pady=1)
        self.var_dither = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            r_misc, text='Дизеринг (для 1-бит)', variable=self.var_dither,
            command=self.refresh_preview
        ).pack(side=tk.LEFT)

        ttk.Label(r_misc, text='RGB565:', width=8).pack(side=tk.LEFT, padx=(16, 2))
        self.var_byte_order = tk.StringVar(value='big')
        ttk.Radiobutton(
            r_misc, text='MSB (SPI)', variable=self.var_byte_order, value='big',
            command=self.refresh_preview
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            r_misc, text='LSB', variable=self.var_byte_order, value='little',
            command=self.refresh_preview
        ).pack(side=tk.LEFT, padx=(6, 0))

        # 4. Звук (Аудио)
        snd_box = ttk.LabelFrame(left_col, text=' 4. Звук (Аудио) ', padding='6')
        snd_box.pack(fill=tk.X, pady=(0, 4))

        r_snd = ttk.Frame(snd_box)
        r_snd.pack(fill=tk.X)
        self.var_audio = tk.StringVar(value='none')
        ttk.Radiobutton(r_snd, text='🔇 Без звука', variable=self.var_audio, value='none', command=self.on_audio_choice_change).pack(side=tk.LEFT)
        ttk.Radiobutton(r_snd, text='🔊 WAV 8кГц (Зуммер)', variable=self.var_audio, value='wav8', command=self.on_audio_choice_change).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(r_snd, text='🔊 WAV 16кГц (Динамик)', variable=self.var_audio, value='wav16', command=self.on_audio_choice_change).pack(side=tk.LEFT, padx=(10, 0))

        self.lbl_audio_status = ttk.Label(snd_box, text='', font=('Segoe UI', 8), foreground='#666')
        self.lbl_audio_status.pack(anchor=tk.W, pady=(2, 0))

        # 5. Куда сохранить результат
        dst_box = ttk.LabelFrame(left_col, text=' 5. Куда сохранить результат ', padding='6')
        dst_box.pack(fill=tk.X, pady=(0, 4))

        self.var_dest = tk.StringVar(value='bin')
        ttk.Radiobutton(
            dst_box, text='📁 Файл для SD карты / SPIFFS (.vid для 1-бит или .rgb565 для цвета)',
            variable=self.var_dest, value='bin'
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            dst_box, text='📄 Исходный код C/C++ (.h массив PROGMEM для Arduino)',
            variable=self.var_dest, value='header'
        ).pack(anchor=tk.W, pady=2)

        # Правая колонка — Предпросмотр и Действия
        right_col = ttk.Frame(content)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        prev_box = ttk.LabelFrame(right_col, text=' Экран устройства (Живой предпросмотр) ', padding='6')
        prev_box.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.canvas_container = ttk.Frame(prev_box)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_container, bg='#0d0d0d', highlightthickness=1, highlightbackground='#333')
        self.canvas.pack(expand=True)

        self.lbl_screen_status = ttk.Label(prev_box, text='128x64 Монохром OLED', font=('Segoe UI', 9, 'bold'), foreground='#0066cc')
        self.lbl_screen_status.pack(pady=(4, 2))

        ctl_row = ttk.Frame(prev_box)
        ctl_row.pack(pady=(2, 2))
        self.btn_play_pause = ttk.Button(ctl_row, text='⏸ Пауза', width=9, command=self.toggle_play_pause)
        self.btn_play_pause.pack(side=tk.LEFT, padx=3)

        btn_rewind = ttk.Button(ctl_row, text='⏮ В начало', width=11, command=self.rewind_video)
        btn_rewind.pack(side=tk.LEFT, padx=3)

        self.lbl_audio_indicator = ttk.Label(ctl_row, text='🔇', font=('Segoe UI', 11))
        self.lbl_audio_indicator.pack(side=tk.LEFT, padx=6)

        # Нижняя панель действий
        act_box = ttk.Frame(right_col)
        act_box.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 0))

        self.pbar = ttk.Progressbar(act_box, mode='determinate')
        self.pbar.pack(fill=tk.X, pady=(0, 4))

        self.lbl_status = ttk.Label(act_box, text='Готов к работе', font=('Segoe UI', 9))
        self.lbl_status.pack(anchor=tk.W, pady=(0, 6))

        btn_act_row = ttk.Frame(act_box)
        btn_act_row.pack(fill=tk.X)

        self.btn_convert = ttk.Button(
            btn_act_row, text='▶ НАЧАТЬ КОНВЕРТАЦИЮ', style='Accent.TButton',
            command=self.start_conversion
        )
        self.btn_convert.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        self.btn_open_folder = ttk.Button(
            btn_act_row, text='📁 Папка', width=9, command=self.open_output_folder
        )
        self.btn_open_folder.pack(side=tk.LEFT, padx=(6, 0), ipady=6)

        # Инициализация профиля
        self.on_profile_change()

    def on_fps_change(self, event=None):
        if self.is_playing:
            if self.play_timer:
                self.root.after_cancel(self.play_timer)
                self.play_timer = None
            self.video_tick()

    def on_contrast_change(self, val):
        self.lbl_contrast_val.config(text=f'{float(val):.1f}x')
        self.refresh_preview()

    def on_brightness_change(self, val):
        self.lbl_bright_val.config(text=f'{float(val):.1f}x')
        self.refresh_preview()

    def refresh_preview(self):
        """Мгновенно перерисовывает текущий кадр в реальном времени при изменении любых параметров."""
        if self.current_raw_frame is not None:
            self.render_preview(self.current_raw_frame)
        elif self.single_image is not None:
            self.current_raw_frame = self.single_image
            self.render_preview(self.current_raw_frame)
        elif self.is_gif and self.gif_frames:
            self.current_raw_frame = self.gif_frames[self.gif_idx % len(self.gif_frames)]
            self.render_preview(self.current_raw_frame)
        elif self.is_video and self.input_file:
            # Чтение текущего кадра без сдвига воспроизведения
            cap = self.preview_cap
            if cap is None:
                cap = cv2.VideoCapture(self.input_file)
            ret, frame = cap.read()
            if ret and frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.current_raw_frame = Image.fromarray(rgb)
                self.render_preview(self.current_raw_frame)

    def get_current_display_config(self):
        prof_key = self.var_profile.get()
        if prof_key == 'Пользовательский (Свой размер...)':
            try:
                w = max(16, int(self.var_custom_w.get()))
                h = max(16, int(self.var_custom_h.get()))
            except ValueError:
                w, h = 128, 64
            shape = self.var_custom_shape.get()
            depth = self.var_custom_depth.get()
            return {
                'width': w, 'height': h, 'shape': shape, 'depth': depth,
                'name': 'Пользовательский'
            }
        cfg = DISPLAY_PROFILES.get(prof_key, list(DISPLAY_PROFILES.values())[0]).copy()
        cfg['name'] = prof_key
        return cfg

    def on_profile_change(self, event=None):
        prof_key = self.var_profile.get()
        if prof_key == 'Пользовательский (Свой размер...)':
            self.f_custom.pack(fill=tk.X, pady=2)
            self.lbl_profile_desc.config(text='Задайте собственные параметры экрана выше.')
        else:
            self.f_custom.pack_forget()
            cfg = DISPLAY_PROFILES.get(prof_key, {})
            self.lbl_profile_desc.config(text=cfg.get('desc', ''))

        self.update_canvas_size()

    def update_canvas_size(self):
        """Динамически изменяет размер и форму Canvas под выбранный дисплей."""
        disp = self.get_current_display_config()
        dw = disp['width']
        dh = disp['height']
        shape = disp['shape']
        depth = disp['depth']

        max_w, max_h = 320, 230
        scale = min(max_w / float(dw), max_h / float(dh))
        cw = max(64, int(dw * scale))
        ch = max(32, int(dh * scale))

        if shape == 'round':
            side = min(cw, ch)
            cw = ch = side

        self.canvas_w = cw
        self.canvas_h = ch
        self.canvas.config(width=cw, height=ch)

        shape_str = 'Круглый Smartwatch' if shape == 'round' else 'Прямоугольный'
        depth_str = 'RGB565 Цвет' if depth == 'rgb565' else '1-бит Монохром'
        self.lbl_screen_status.config(text=f"{dw}x{dh} ({shape_str}, {depth_str})")

        if self.current_raw_frame is not None:
            self.refresh_preview()
        else:
            placeholder = Image.new('RGB', (cw, ch), (13, 13, 13) if shape == 'round' else (0, 0, 0))
            draw = ImageDraw.Draw(placeholder)
            if shape == 'round':
                draw.ellipse((0, 0, cw - 1, ch - 1), fill=(0, 0, 0), outline=(90, 90, 90), width=2)
                draw.ellipse((2, 2, cw - 3, ch - 3), outline=(40, 40, 40), width=1)
            else:
                draw.rectangle((0, 0, cw - 1, ch - 1), fill=(0, 0, 0), outline=(60, 60, 60), width=1)
            self.tk_preview = ImageTk.PhotoImage(placeholder)
            self.canvas.delete('all')
            self.canvas.create_image(cw // 2, ch // 2, image=self.tk_preview)

    def browse_file(self):
        filetypes = [
            ('Все поддерживаемые форматы', '*.mp4 *.avi *.mov *.mkv *.webm *.gif *.jpg *.png *.jpeg *.webp *.bmp'),
            ('Видео файлы', '*.mp4 *.avi *.mov *.mkv *.webm'),
            ('Анимации GIF', '*.gif'),
            ('Изображения', '*.jpg *.png *.jpeg *.webp *.bmp'),
            ('Все файлы', '*.*')
        ]
        chosen = filedialog.askopenfilename(title='Выберите видео, GIF или фото', filetypes=filetypes)
        if chosen:
            self.load_input_file(chosen)

    def load_input_file(self, filepath):
        self.stop_playback()
        self.input_file = filepath
        self.lbl_filename.config(text=os.path.basename(filepath), foreground='#000')

        self.is_video = False
        self.is_gif = False
        self.single_image = None
        self.current_raw_frame = None
        self.gif_frames = []
        self.gif_idx = 0

        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.gif':
            try:
                pil_img = Image.open(filepath)
                self.gif_frames = [f.copy().convert('RGB') for f in ImageSequence.Iterator(pil_img)]
                self.total_frames = len(self.gif_frames)
                self.src_fps = 12.0
                self.duration = self.total_frames / 12.0
                self.has_audio = False
                self.is_gif = True
                self.current_raw_frame = self.gif_frames[0] if self.gif_frames else None
                w, h = pil_img.size
            except Exception as e:
                messagebox.showerror('Ошибка', f'Не удалось открыть GIF:\n{e}')
                return
        elif ext in ('.jpg', '.jpeg', '.png', '.webp', '.bmp'):
            try:
                pil_img = Image.open(filepath).convert('RGB')
                self.single_image = pil_img
                self.current_raw_frame = pil_img
                self.total_frames = 1
                self.src_fps = 1.0
                self.duration = 0.0
                self.has_audio = False
                w, h = pil_img.size
            except Exception as e:
                messagebox.showerror('Ошибка', f'Не удалось открыть картинку:\n{e}')
                return
        else:
            # Видеофайл через OpenCV
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                messagebox.showerror('Ошибка', 'Не удалось открыть видеофайл через OpenCV.')
                return
            self.src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
            self.duration = self.total_frames / max(1.0, self.src_fps)

            # Прочитать первый кадр для мгновенного предпросмотра
            ret, frame = cap.read()
            if ret and frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.current_raw_frame = Image.fromarray(rgb)
            cap.release()
            self.is_video = True

            # Проверка аудиодорожки через ffmpeg
            self.has_audio = False
            if FFMPEG_EXE:
                try:
                    kwargs = {}
                    if sys.platform == 'win32':
                        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                    res = subprocess.run([FFMPEG_EXE, '-i', filepath], stderr=subprocess.PIPE, text=True, **kwargs)
                    if 'Audio:' in res.stderr:
                        self.has_audio = True
                except Exception:
                    pass

        audio_str = 'Звук: Есть' if self.has_audio else 'Звук: Нет'
        self.lbl_info.config(
            text=f"{w}x{h} | {self.src_fps:.1f} FPS | Кадров: {self.total_frames} (~{self.duration:.1f} сек) | {audio_str}"
        )

        if self.has_audio:
            self.lbl_audio_status.config(text='В исходном файле: аудиодорожка найдена')
            self.extract_preview_audio()
        else:
            self.lbl_audio_status.config(text='В исходном файле: аудиодорожка отсутствует')
            self.var_audio.set('none')

        self.start_playback()

    def extract_preview_audio(self):
        """Извлекает аудиодорожку во временный WAV для синхронного предпросмотра."""
        try:
            kwargs = {}
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            cmd = [FFMPEG_EXE, '-y', '-i', self.input_file, '-vn', '-ac', '2', '-ar', '44100', self.temp_wav]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        except Exception:
            pass

    def start_playback(self):
        if not self.input_file:
            return
        if self.is_video and self.preview_cap is None:
            self.preview_cap = cv2.VideoCapture(self.input_file)
        self.is_playing = True
        self.btn_play_pause.config(text='⏸ Пауза')
        self.sync_audio(restart=False)
        self.video_tick()

    def stop_playback(self):
        self.is_playing = False
        if self.play_timer:
            self.root.after_cancel(self.play_timer)
            self.play_timer = None
        self.stop_audio()
        self.btn_play_pause.config(text='▶ Играть')

    def toggle_play_pause(self):
        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()

    def rewind_video(self):
        if self.preview_cap and self.is_video:
            self.preview_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.preview_cap.read()
            if ret and frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.current_raw_frame = Image.fromarray(rgb)
                self.render_preview(self.current_raw_frame)
        self.gif_idx = 0
        if self.is_gif and self.gif_frames:
            self.current_raw_frame = self.gif_frames[0]
            self.render_preview(self.current_raw_frame)
        self.sync_audio(restart=True)

    def on_audio_choice_change(self):
        if self.var_audio.get() == 'none':
            self.stop_audio()
            self.lbl_audio_indicator.config(text='🔇')
        else:
            self.lbl_audio_indicator.config(text='🔊')
            if self.is_playing:
                self.sync_audio(restart=True)

    def sync_audio(self, restart=False):
        if not self.has_audio or self.var_audio.get() == 'none':
            self.stop_audio()
            return
        if not os.path.isfile(self.temp_wav):
            return
        try:
            import winsound
            if restart or not self.audio_playing:
                winsound.PlaySound(self.temp_wav, winsound.SND_ASYNC | winsound.SND_FILENAME)
                self.audio_playing = True
                self.lbl_audio_indicator.config(text='🔊')
        except Exception:
            pass

    def stop_audio(self):
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        self.audio_playing = False
        if self.var_audio.get() == 'none':
            self.lbl_audio_indicator.config(text='🔇')

    def video_tick(self):
        """Основной цикл кадровой анимации предпросмотра."""
        frame_img = None

        if self.single_image:
            frame_img = self.single_image
        elif self.is_gif and self.gif_frames:
            frame_img = self.gif_frames[self.gif_idx]
            if self.is_playing:
                self.gif_idx = (self.gif_idx + 1) % len(self.gif_frames)
        elif self.is_video and self.preview_cap:
            ret, frame = self.preview_cap.read()
            if not ret:
                # Зацикливание видео
                self.preview_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.preview_cap.read()
                if self.is_playing:
                    self.sync_audio(restart=True)
            if ret and frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_img = Image.fromarray(rgb)

        if frame_img:
            self.current_raw_frame = frame_img
            self.render_preview(frame_img)

        if self.is_playing and (self.is_video or self.is_gif):
            fps_choice = self.var_fps.get()
            if fps_choice != 'auto':
                try:
                    fps = float(fps_choice.split()[0])
                except Exception:
                    fps = self.src_fps
            else:
                fps = self.src_fps
            fps = min(60.0, max(5.0, fps))
            delay_ms = int(1000.0 / fps)
            self.play_timer = self.root.after(delay_ms, self.video_tick)

    def render_preview(self, pil_img):
        """Преобразует кадр под параметры выбранного дисплея и рисует на холсте."""
        disp = self.get_current_display_config()
        dw = disp['width']
        dh = disp['height']
        shape = disp['shape']
        depth = disp['depth']
        cw = getattr(self, 'canvas_w', 256)
        ch = getattr(self, 'canvas_h', 128)

        contrast = round(self.var_contrast.get(), 2)
        bright = round(self.var_brightness.get(), 2)

        self.lbl_contrast_val.config(text=f'{contrast}x')
        self.lbl_bright_val.config(text=f'{bright}x')

        img = pil_img.copy()
        if bright != 1.0:
            img = ImageEnhance.Brightness(img).enhance(bright)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)

        if self.var_scale.get() == 'fit':
            fitted = ImageOps.fit(img, (dw, dh), method=Image.Resampling.BILINEAR)
        else:
            fitted = ImageOps.pad(img, (dw, dh), color=(0, 0, 0), method=Image.Resampling.BILINEAR)

        if depth == '1bit':
            gray = fitted.convert('L')
            processed = gray.convert(
                '1',
                dither=Image.Dither.FLOYDSTEINBERG if self.var_dither.get() else Image.Dither.NONE
            ).convert('RGB')
        else:
            # Квантование RGB565 для точного предпросмотра
            arr = np.array(fitted, dtype=np.uint8)
            r = (arr[:, :, 0] >> 3) << 3
            g = (arr[:, :, 1] >> 2) << 2
            b = (arr[:, :, 2] >> 3) << 3
            processed = Image.fromarray(np.stack([r, g, b], axis=-1))

        disp_img = processed.resize((cw, ch), Image.Resampling.NEAREST)

        if shape == 'round':
            mask = Image.new('L', (cw, ch), 0)
            draw_m = ImageDraw.Draw(mask)
            draw_m.ellipse((0, 0, cw, ch), fill=255)
            final_img = Image.new('RGB', (cw, ch), (13, 13, 13))
            final_img.paste(disp_img, (0, 0), mask)
            draw_c = ImageDraw.Draw(final_img)
            draw_c.ellipse((0, 0, cw - 1, ch - 1), outline=(90, 90, 90), width=2)
            draw_c.ellipse((2, 2, cw - 3, ch - 3), outline=(40, 40, 40), width=1)
        else:
            final_img = disp_img
            draw_c = ImageDraw.Draw(final_img)
            draw_c.rectangle((0, 0, cw - 1, ch - 1), outline=(60, 60, 60), width=1)

        self.tk_preview = ImageTk.PhotoImage(final_img)
        self.canvas.delete('all')
        self.canvas.create_image(cw // 2, ch // 2, image=self.tk_preview)

    def start_conversion(self):
        if not self.input_file:
            messagebox.showwarning('Внимание', 'Сначала выберите файл для конвертации.')
            return

        self.stop_playback()
        self.btn_convert.config(state=tk.DISABLED)
        threading.Thread(target=self.run_conversion_thread, daemon=True).start()

    def run_conversion_thread(self):
        input_path = self.input_file
        base, _ = os.path.splitext(input_path)
        disp = self.get_current_display_config()
        dw, dh = disp['width'], disp['height']
        shape = disp['shape']
        depth = disp['depth']

        dest_mode = self.var_dest.get()
        byte_order = self.var_byte_order.get()

        output_ext = '.vid' if depth == '1bit' else '.rgb565'
        if dest_mode == 'header':
            output_ext = '.h'

        output_main = base + output_ext
        output_wav = base + '.wav'

        fps_choice = self.var_fps.get()
        if fps_choice == 'auto':
            target_fps = int(round(self.src_fps)) if self.src_fps > 0 else 12
        else:
            try:
                target_fps = int(fps_choice.split()[0])
            except Exception:
                target_fps = 12

        contrast = round(self.var_contrast.get(), 2)
        bright = round(self.var_brightness.get(), 2)
        dither = self.var_dither.get()
        scale_mode = self.var_scale.get()
        audio_choice = self.var_audio.get()
        extract_audio = (audio_choice in ('wav8', 'wav16')) and self.has_audio

        self.lbl_status.config(text=f"Конвертация: {dw}x{dh} @ {target_fps} FPS...")
        self.pbar['value'] = 0

        # Извлечение аудио через ffmpeg
        if extract_audio and FFMPEG_EXE:
            ar = '8000' if audio_choice == 'wav8' else '16000'
            self.lbl_status.config(text=f"Извлечение аудио ({ar} Гц)...")
            cmd = [FFMPEG_EXE, '-y', '-i', input_path, '-vn', '-ac', '1', '-ar', ar, '-c:a', 'pcm_u8', output_wav]
            kwargs = {}
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            except Exception:
                pass

        # Подготовка круглой маски
        round_mask = None
        if shape == 'round':
            round_mask = Image.new('L', (dw, dh), 0)
            draw_rm = ImageDraw.Draw(round_mask)
            draw_rm.ellipse((0, 0, dw, dh), fill=255)

        def encode_frame(pil_im):
            if bright != 1.0:
                pil_im = ImageEnhance.Brightness(pil_im).enhance(bright)
            if contrast != 1.0:
                pil_im = ImageEnhance.Contrast(pil_im).enhance(contrast)

            if scale_mode == 'fit':
                fitted = ImageOps.fit(pil_im, (dw, dh), method=Image.Resampling.BILINEAR)
            else:
                fitted = ImageOps.pad(pil_im, (dw, dh), color=(0, 0, 0), method=Image.Resampling.BILINEAR)

            if shape == 'round' and round_mask:
                bg = Image.new('RGB', (dw, dh), (0, 0, 0))
                bg.paste(fitted, (0, 0), round_mask)
                fitted = bg

            if depth == '1bit':
                gray = fitted.convert('L')
                bw = gray.convert(
                    '1',
                    dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
                )
                return bw.tobytes()
            else:
                arr = np.array(fitted, dtype=np.uint16)
                r = arr[:, :, 0]
                g = arr[:, :, 1]
                b = arr[:, :, 2]
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                if byte_order == 'big':
                    return rgb565.byteswap().tobytes()
                return rgb565.tobytes()

        # Открытие выходного файла
        f_bin = None
        if dest_mode == 'bin':
            f_bin = open(output_main, 'wb')

        frames_written = 0
        frames_bytes_list = []
        start_t = time.time()
        ext = os.path.splitext(input_path)[1].lower()

        try:
            if ext == '.gif':
                pil_img = Image.open(input_path)
                for f_pil in ImageSequence.Iterator(pil_img):
                    b_data = encode_frame(f_pil.convert('RGB'))
                    if f_bin:
                        f_bin.write(b_data)
                    if dest_mode == 'header':
                        frames_bytes_list.append(b_data)
                    frames_written += 1
            elif ext in ('.jpg', '.jpeg', '.png', '.webp', '.bmp'):
                pil_img = Image.open(input_path).convert('RGB')
                b_data = encode_frame(pil_img)
                if f_bin:
                    f_bin.write(b_data)
                if dest_mode == 'header':
                    frames_bytes_list.append(b_data)
                frames_written = 1
            else:
                # Чтение видео через OpenCV с субсэмплингом FPS
                cap = cv2.VideoCapture(input_path)
                total_src_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
                src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

                ratio = src_fps / float(target_fps) if target_fps > 0 else 1.0
                next_keep = 0.0
                src_idx = 0

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    if src_idx >= next_keep:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        b_data = encode_frame(Image.fromarray(rgb))
                        if f_bin:
                            f_bin.write(b_data)
                        if dest_mode == 'header':
                            frames_bytes_list.append(b_data)
                        frames_written += 1
                        next_keep += ratio

                        if frames_written % 10 == 0:
                            pct = min(100, int((src_idx / max(1, total_src_frames)) * 100))
                            self.pbar['value'] = pct
                            sec = frames_written / float(target_fps)
                            self.lbl_status.config(text=f"Кадр {frames_written} ({pct}%) — {sec:.1f} сек...")

                    src_idx += 1
                cap.release()

            if f_bin:
                f_bin.close()

            self.pbar['value'] = 100
            elapsed = time.time() - start_t
            file_kb = os.path.getsize(output_main) / 1024.0 if dest_mode == 'bin' else 0

            # Генерация C/C++ заголовочного файла (.h)
            if dest_mode == 'header' and frames_bytes_list:
                var_name = os.path.splitext(os.path.basename(input_path))[0].replace('-', '_').replace(' ', '_').lower()
                with open(output_main, 'w', encoding='utf-8') as f_hdr:
                    f_hdr.write('#pragma once\n')
                    f_hdr.write('// Экспортировано OLED & TFT Converter\n')
                    f_hdr.write(f"// Дисплей: {disp['name']} ({dw}x{dh}), Кадров: {len(frames_bytes_list)}, FPS: {target_fps}\n")
                    f_hdr.write('#include <Arduino.h>\n\n')
                    f_hdr.write(f'#define {var_name.upper()}_WIDTH {dw}\n')
                    f_hdr.write(f'#define {var_name.upper()}_HEIGHT {dh}\n')
                    f_hdr.write(f'#define {var_name.upper()}_FRAMES {len(frames_bytes_list)}\n\n')

                    if len(frames_bytes_list) == 1:
                        if depth == '1bit':
                            f_hdr.write(f'const uint8_t {var_name}_bitmap[{len(frames_bytes_list[0])}] PROGMEM = {{\n  ')
                            for idx, b in enumerate(frames_bytes_list[0]):
                                f_hdr.write(f'0x{b:02X}')
                                if idx < len(frames_bytes_list[0]) - 1:
                                    f_hdr.write(',' + ('\n  ' if (idx + 1) % 16 == 0 else ' '))
                            f_hdr.write('\n};\n')
                        else:
                            f_hdr.write(f'const uint16_t {var_name}_rgb565[{dw * dh}] PROGMEM = {{\n  ')
                            u16_vals = np.frombuffer(frames_bytes_list[0], dtype=np.uint16)
                            for idx, val in enumerate(u16_vals):
                                f_hdr.write(f'0x{val:04X}')
                                if idx < len(u16_vals) - 1:
                                    f_hdr.write(',' + ('\n  ' if (idx + 1) % 12 == 0 else ' '))
                            f_hdr.write('\n};\n')
                    else:
                        f_hdr.write(f'const uint8_t {var_name}_data[{len(frames_bytes_list)}][{len(frames_bytes_list[0])}] PROGMEM = {{\n')
                        for i, fb in enumerate(frames_bytes_list):
                            f_hdr.write(f'  // Кадр {i + 1}\n  {{\n    ')
                            for b_i, b in enumerate(fb):
                                f_hdr.write(f'0x{b:02X}')
                                if b_i < len(fb) - 1:
                                    f_hdr.write(',' + ('\n    ' if (b_i + 1) % 16 == 0 else ' '))
                            f_hdr.write('\n  }' + (',\n' if i < len(frames_bytes_list) - 1 else '\n'))
                        f_hdr.write('};\n')

                file_kb = os.path.getsize(output_main) / 1024.0

            res_text = f"Готово! {frames_written} кадров ({file_kb:.1f} КБ) за {elapsed:.1f} сек."
            self.lbl_status.config(text=res_text)

            msg = (
                f"Конвертация завершена успешно!\n\n"
                f"Дисплей: {disp['name']} ({dw}x{dh}, {depth})\n"
                f"Файл: {os.path.basename(output_main)} ({file_kb:.1f} КБ)\n"
                f"Кадров: {frames_written} при {target_fps} FPS (~{frames_written / float(target_fps):.1f} сек)\n"
                + (f"\nАудио: {os.path.basename(output_wav)}" if extract_audio else "")
            )
            messagebox.showinfo('Готово!', msg)

        except Exception as e:
            self.lbl_status.config(text=f"Ошибка: {e}")
            messagebox.showerror('Ошибка', f'Произошла ошибка при конвертации:\n{e}')

        finally:
            self.btn_convert.config(state=tk.NORMAL)
            self.start_playback()

    def open_output_folder(self):
        folder = os.path.dirname(self.input_file) if self.input_file and os.path.exists(os.path.dirname(self.input_file)) else get_base_dir()
        if os.path.exists(folder):
            os.startfile(folder)

    def on_close(self):
        self.stop_playback()
        if self.preview_cap:
            try:
                self.preview_cap.release()
            except Exception:
                pass
            self.preview_cap = None
        try:
            if os.path.isfile(self.temp_wav):
                os.remove(self.temp_wav)
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = OledConverterApp(root)
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        root.after(100, lambda: app.load_input_file(sys.argv[1]))
    root.mainloop()


if __name__ == '__main__':
    main()
