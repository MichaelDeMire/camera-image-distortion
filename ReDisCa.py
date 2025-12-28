import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
from datetime import datetime
import os
import sys
import threading
import sounddevice as sd
import wave
import struct

class VideoCameraApp:
    def __init__(self, window):
        self.window = window
        self.language = "ru"
        self.translations = {
            "ru": {
                "title": "Камера с эффектами",
                "start_rec": "⏺ Начать запись",
                "stop_rec": "⏹ Остановить запись",
                "take_photo": "📸 Сфотографировать",
                "select_folder": "📁 Выбрать папку",
                "open_folder": "📂 Открыть папку",
                "apply": "Применить формулу",
                "clear": "Очистить формулу",
                "formula": "Формула эффекта:",
                "functions": "Доступные функции:",
                "ready": "Готов",
                "recording": "Идет запись в",
                "saved": "Сохранено в",
                "no_camera": "Не удалось открыть камеру",
                "no_folder": "Сначала выберите папку",
                "photo_saved": "Фото сохранено как:",
                "change_lang": "EN",
                "folder": "Папка:",
                "not_selected": "не выбрана"
            },
            "en": {
                "title": "Video Camera with Effects",
                "start_rec": "⏺ Start Recording",
                "stop_rec": "⏹ Stop Recording",
                "take_photo": "📸 Take Photo",
                "select_folder": "📁 Select Folder",
                "open_folder": "📂 Open folder",
                "apply": "Apply Formula",
                "clear": "Clear Formula",
                "formula": "Effect Formula:",
                "functions": "Available Functions:",
                "ready": "Ready",
                "recording": "Recording to",
                "saved": "Saved to",
                "no_camera": "Could not open camera",
                "no_folder": "Please select folder first",
                "photo_saved": "Photo saved as:",
                "change_lang": "RU",
                "folder": "Folder:",
                "not_selected": "not selected"
            }
        }
        
        self.setup_camera()
        self.create_widgets()
        self.update_frame()
    
    def setup_camera(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            messagebox.showerror("Error", self._tr("no_camera"))
            exit()
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Video settings
        self.is_recording = False
        self.video_writer = None
        self.audio_recording = None
        self.audio_frames = []
        self.fps = 24
        self.save_path = ""
        self.frame_count = 0
        self.last_frame_time = 0
        
        # Math functions
        self.math_funcs = {
            'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
            'arcsin': np.arcsin, 'arccos': np.arccos, 'arctan': np.arctan,
            'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
            'pi': np.pi, 'e': np.exp(1), 'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt
        }
        
        self.current_frame = None
        self.distorted_frame = None
        self.formula = "50*sinh(x)"
        self.imgtk = None
        self.last_formula_error = False
    
    def _tr(self, key):
        return self.translations[self.language].get(key, key)
    
    def change_language(self):
        self.language = "en" if self.language == "ru" else "ru"
        self.update_ui_text()
    
    def update_ui_text(self):
        self.window.title(self._tr("title"))
        self.record_btn.config(text=self._tr("stop_rec" if self.is_recording else "start_rec"))
        self.lang_btn.config(text=self._tr("change_lang"))
        self.take_photo_btn.config(text=self._tr("take_photo"))
        self.select_folder_btn.config(text=self._tr("select_folder"))
        self.open_folder_btn.config(text=self._tr("open_folder"))
        self.apply_btn.config(text=self._tr("apply"))
        self.clear_btn.config(text=self._tr("clear"))
        self.formula_label.config(text=self._tr("formula"))
        self.functions_label.config(text=self._tr("functions"))
    
        if self.save_path:
            display_path = self.save_path[:30] + "..." if len(self.save_path) > 30 else self.save_path
            self.path_label.config(text=f"{self._tr('folder')} {display_path}")
        else:
            self.path_label.config(text=f"{self._tr('folder')} {self._tr('not_selected')}")
    
        if self.is_recording:
            self.status_var.set(f"{self._tr('recording')} {self.video_filename}")
        else:
            self.status_var.set(self._tr("ready"))
    
    def create_widgets(self):
        self.window.title(self._tr("title"))
        self.window.minsize(800, 600)
        self.window.geometry("1000x700")
        
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top control panel
        top_frame = tk.Frame(main_frame, height=40)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        top_frame.pack_propagate(False)
        
        # Language button
        self.lang_btn = tk.Button(top_frame, text=self._tr("change_lang"), command=self.change_language)
        self.lang_btn.pack(side=tk.RIGHT, padx=5)
        
        # Recording controls
        self.record_btn = tk.Button(top_frame, text=self._tr("start_rec"), command=self.toggle_recording)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        # Photo controls
        self.take_photo_btn = tk.Button(top_frame, text=self._tr("take_photo"), command=self.take_photo)
        self.take_photo_btn.pack(side=tk.LEFT, padx=5)
        
        self.select_folder_btn = tk.Button(top_frame, text=self._tr("select_folder"), command=self.select_folder)
        self.select_folder_btn.pack(side=tk.LEFT, padx=5)
        
        self.path_label = tk.Label(top_frame, text=f"{self._tr('folder')} {self._tr('not_selected')}", fg="blue")
        self.path_label.pack(side=tk.LEFT, padx=10)

        # Добавляем новую кнопку в панель управления
        self.open_folder_btn = tk.Button(top_frame, text=self._tr("open_folder"), command=self.open_save_folder)
        self.open_folder_btn.pack(side=tk.LEFT, padx=5)
        
        # Main work area
        work_frame = tk.Frame(main_frame)
        work_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel with functions
        left_frame = tk.Frame(work_frame, width=200, bg='#f0f0f0')
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        self.functions_label = tk.Label(left_frame, text=self._tr("functions"), bg='#f0f0f0')
        self.functions_label.pack(pady=5)
        
        func_list = [
            "sin(x), cos(x), tan(x)",
            "arcsin(x), arccos(x), arctan(x)",
            "sinh(x), cosh(x), tanh(x)",
            "pi (3.1415...)",
            "e (2.7182...)",
            "exp(x) - e^x",
            "log(x) - натуральный логарифм",
            "sqrt(x) - квадратный корень",
            "x**2 - квадрат числа",
            "a*b - умножение",
            "a/b - деление"
        ]
        
        for func in func_list:
            tk.Label(left_frame, text=func, anchor='w', bg='#f0f0f0').pack(fill=tk.X, padx=5, pady=2)
        
        # Camera area
        camera_frame = tk.Frame(work_frame)
        camera_frame.pack(fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Formula panel (bottom)
        formula_frame = tk.Frame(camera_frame)
        formula_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        self.formula_label = tk.Label(formula_frame, text=self._tr("formula"))
        self.formula_label.pack(side=tk.LEFT)
        
        self.entry = tk.Entry(formula_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry.insert(0, self.formula)
        
        self.apply_btn = tk.Button(formula_frame, text=self._tr("apply"), command=self.apply_formula)
        self.apply_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = tk.Button(formula_frame, text=self._tr("clear"), command=self.clear_formula)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Camera display
        self.camera_label = tk.Label(camera_frame, bg='black')
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set(self._tr("ready"))
        tk.Label(main_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X)
    
    def apply_formula(self):
        self.formula = self.entry.get().replace("^", "**").replace(" ", "")
    
        # Проверка на использование только допустимой переменной x
        variables = set()
        try:
            # Анализируем формулу на предмет переменных
            from ast import parse, walk, Name
            tree = parse(self.formula)
            variables = {node.id for node in walk(tree) if isinstance(node, Name)}
            variables.discard('x')  # Разрешаем только x
            variables.difference_update(self.math_funcs.keys())  # Игнорируем функции
        
            if variables:
                raise ValueError(f"Используйте только 'x' как переменную или проверьте правильность написания функции из доступных. Найдены: {', '.join(variables)}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return False

        # Проверка на доступные функции
        try:
            # Извлекаем все имена из формулы
            import re
            words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', self.formula)
            invalid_funcs = [w for w in words if w not in self.math_funcs and w != 'x']
        
            if invalid_funcs:
                available = ", ".join(sorted(self.math_funcs.keys()))
                raise ValueError(f"Неизвестные функции: {', '.join(invalid_funcs)}\nДоступные: {available}")

            # Проверяем синтаксис и вычисляемость
            test_x = np.linspace(0.1, 10, 10)  # Начинаем с 0.1 для log
            with np.errstate(all='ignore'):
                result = eval(self.formula, {'x': test_x, **self.math_funcs})
                if np.any(np.isnan(result)) or np.any(np.isinf(result)):
                    raise ValueError("Формула дает недопустимые значения")
        
            self.last_formula_error = False
            return True
        
        except SyntaxError:
            messagebox.showerror("Ошибка", "Неправильный синтаксис формулы")
            return False
        except Exception as e:
            error_msg = str(e)
            if "name" in error_msg and "is not defined" in error_msg:
                # Извлекаем имя из сообщения об ошибке
                missing = error_msg.split("'")[1]
                if missing in ['sin1', 'log2']:  # Примеры неправильных функций
                    error_msg = f"Функция '{missing}' не существует. Проверьте написание."
                else:
                    error_msg = f"Неизвестный идентификатор: '{missing}'"
        
            messagebox.showerror("Ошибка", error_msg)
            self.last_formula_error = True
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.formula)
            return False

    
    
    def clear_formula(self):
        self.entry.delete(0, tk.END)
        self.formula = ""
        self.last_formula_error = False
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        if not self.save_path:
            messagebox.showwarning("Warning", self._tr("no_folder"))
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_filename = os.path.join(self.save_path, f"video_{timestamp}.avi")
        
        # Video settings
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Используем кодек MJPG и формат AVI для совместимости
        self.video_writer = cv2.VideoWriter(
            self.video_filename,
            cv2.VideoWriter_fourcc('M','J','P','G'),
            30,  # Фиксированные 30 FPS
            (width, height))
            
        if not self.video_writer.isOpened():
            messagebox.showerror("Error", "Не удалось инициализировать запись видео")
            return
        
        # Audio settings
        self.audio_frames = []
        self.audio_recording = True
        self.audio_thread = threading.Thread(
            target=self.record_audio,
            daemon=True)
        self.audio_thread.start()
        
        self.is_recording = True
        self.frame_count = 0
        self.last_frame_time = datetime.now().timestamp()
        self.record_btn.config(text=self._tr("stop_rec"), fg="red")
        self.status_var.set(f"{self._tr('recording')} {self.video_filename}")
        self.update_ui_text()
    
    def stop_recording(self):
        self.is_recording = False
        self.audio_recording = False
        
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            
        if len(self.audio_frames) > 0:
            self.save_audio_video()  # Сохраняем видео с аудио
            
        self.record_btn.config(text=self._tr("start_rec"), fg="black")
        self.status_var.set(f"{self._tr('saved')} {self.video_filename}")
        self.update_ui_text()
    
    def record_audio(self):
        """Записывает аудио в отдельном потоке"""
        with sd.InputStream(
            samplerate=44100,
            channels=2,
            dtype='int16',  # Используем int16 для совместимости с WAV
            blocksize=1024,
            device=None) as stream:
            
            while self.audio_recording:
                data, overflowed = stream.read(1024)
                if overflowed:
                    print("Audio overflow!")
                self.audio_frames.append(data)
    
    def save_audio_video(self):
    #Сохраняет видео с аудио в AVI файле
        try:
            if len(self.audio_frames) > 0:
                audio_filename = os.path.join(self.save_path, f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
                with wave.open(audio_filename, 'wb') as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(44100)
                    wf.writeframes(np.concatenate(self.audio_frames).tobytes())
        except Exception as e:
            print(f"Ошибка сохранения аудио: {e}")
    
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            try:
            # Проверяем возможность записи в папку
                test_file = os.path.join(folder, 'test.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            
                self.save_path = folder
                display_path = folder[:30] + "..." if len(folder) > 30 else folder
                self.path_label.config(text=f"{self._tr('folder')} {display_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Невозможно записать в выбранную папку: {e}")
        
    def open_save_folder(self):
        """Открывает проводник с папкой сохранения"""
        if not self.save_path:
            messagebox.showwarning(
                self._tr("warning"), 
                self._tr("no_folder")
            )
            return
    
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.save_path)
            elif os.name == 'posix':  # macOS/Linux
                if platform.system() == 'Darwin':
                    subprocess.run(['open', self.save_path])
                else:
                    subprocess.run(['xdg-open', self.save_path])
        except Exception as e:
            messagebox.showerror(
                self._tr("error"),
                f"{self._tr('folder_open_error')}: {str(e)}"
            )
    def take_photo(self):
        if self.distorted_frame is None:
            messagebox.showwarning("Warning", "Нет данных с камеры")
            return
            
        if not self.save_path:
            messagebox.showwarning("Warning", self._tr("no_folder"))
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.save_path, f"photo_{timestamp}.jpg")
        
        try:
            cv2.imwrite(filename, self.distorted_frame)
            messagebox.showinfo("Успех", f"{self._tr('photo_saved')}\n{filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить фото: {e}")
    
    def distort_image(self, frame):
        if not self.formula:
            return frame
        try:
            height, width = frame.shape[:2]
            x = np.linspace(-10, 10, width)
        
        # Вычисляем формулу с обработкой ошибок
            with np.errstate(all='ignore'):  # Игнорируем предупреждения
                y = eval(self.formula, {'x': x, **self.math_funcs})
                y = np.nan_to_num(y)  # Заменяем NaN на 0
            
            y_min, y_max = np.min(y), np.max(y)
            if y_max - y_min > 0:
                y = (y - y_min) / (y_max - y_min) * height
            else:
                y = np.zeros_like(y)
        
            xx, yy = np.meshgrid(np.arange(width), np.arange(height))
            map_y = yy + y - height//2
        
            return cv2.remap(frame, 
                        xx.astype(np.float32), 
                        map_y.astype(np.float32),
                        interpolation=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE)
        except Exception as e:
            print(f"Ошибка в формуле: {e}")
            return frame  
    
    
    def update_frame(self):
        try:
            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError("Не удалось получить кадр с камеры")
            
            self.current_frame = frame.copy()
            self.distorted_frame = self.distort_image(frame)

            # Записываем кадры с правильным FPS
            if self.is_recording and self.video_writer:
                self.video_writer.write(self.distorted_frame)
            
            # Масштабируем для отображения
            label_width = self.camera_label.winfo_width()
            label_height = self.camera_label.winfo_height()
            
            if label_width > 10 and label_height > 10:
                h, w = self.distorted_frame.shape[:2]
                ratio = min(label_width/w, label_height/h)
                new_size = (int(w*ratio), int(h*ratio))
                display_frame = cv2.resize(self.distorted_frame, new_size)
                
                display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(display_frame)
                self.imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.config(image=self.imgtk)
        except Exception as e:
            print(f"Ошибка в update_frame: {e}")
        finally:
            self.window.after(30, self.update_frame)

    
    def run(self):
        self.window.mainloop()
        if self.is_recording:
            self.stop_recording()
        self.cap.release()

if __name__ == "__main__":
    try:
        import sounddevice as sd
    except ImportError:
        print("Для работы с аудио установите:")
        print("pip install sounddevice")
        sys.exit(1)
        
    root = tk.Tk()
    app = VideoCameraApp(root)
    app.run()