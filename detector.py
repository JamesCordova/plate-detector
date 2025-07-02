import cv2
import easyocr
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import numpy as np
import os

class PlateDetectorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Detector de Placas - Cámaras IP")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Variables de estado
        self.reader = easyocr.Reader(["es", "en"], gpu=False)
        self.allowed_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        self.available_cameras = []
        self.current_camera = None
        self.is_streaming = False
        self.cap = None
        self.detection_enabled = True
        self.save_detections = False
        
        # Variables de interfaz
        self.video_label = None
        self.status_var = tk.StringVar(value="Listo")
        self.camera_var = tk.StringVar(value="No hay cámaras")
        self.detection_var = tk.BooleanVar(value=True)
        self.save_var = tk.BooleanVar(value=False)
        
        self.setup_ui()
        self.scan_cameras_async()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#2b2b2b', foreground='white')
        style.configure('Subtitle.TLabel', font=('Arial', 10), background='#2b2b2b', foreground='#cccccc')
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel superior - Controles
        control_frame = tk.Frame(main_frame, bg='#3b3b3b', relief=tk.RAISED, bd=2)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Título
        title_label = ttk.Label(control_frame, text="🚗 Detector de Placas con Cámaras IP", style='Title.TLabel')
        title_label.pack(pady=10)
        
        # Controles de cámara
        camera_frame = tk.Frame(control_frame, bg='#3b3b3b')
        camera_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(camera_frame, text="Cámara:", bg='#3b3b3b', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.camera_combo = ttk.Combobox(camera_frame, textvariable=self.camera_var, state='readonly', width=40)
        self.camera_combo.pack(side=tk.LEFT, padx=(10, 5))
        self.camera_combo.bind('<<ComboboxSelected>>', self.on_camera_selected)
        
        refresh_btn = tk.Button(camera_frame, text="🔄 Buscar", command=self.scan_cameras_async, 
                               bg='#4CAF50', fg='white', font=('Arial', 9, 'bold'), relief=tk.FLAT)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Controles de stream
        stream_frame = tk.Frame(control_frame, bg='#3b3b3b')
        stream_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.start_btn = tk.Button(stream_frame, text="▶ Iniciar", command=self.start_stream,
                                  bg='#2196F3', fg='white', font=('Arial', 10, 'bold'), relief=tk.FLAT, width=8)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = tk.Button(stream_frame, text="⏸ Detener", command=self.stop_stream,
                                 bg='#f44336', fg='white', font=('Arial', 10, 'bold'), relief=tk.FLAT, width=8, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        capture_btn = tk.Button(stream_frame, text="📷 Capturar", command=self.capture_image,
                               bg='#FF9800', fg='white', font=('Arial', 10, 'bold'), relief=tk.FLAT, width=10)
        capture_btn.pack(side=tk.LEFT, padx=5)
        
        file_btn = tk.Button(stream_frame, text="📁 Abrir Imagen", command=self.open_image_file,
                            bg='#9C27B0', fg='white', font=('Arial', 10, 'bold'), relief=tk.FLAT, width=12)
        file_btn.pack(side=tk.LEFT, padx=5)
        
        # Opciones
        options_frame = tk.Frame(control_frame, bg='#3b3b3b')
        options_frame.pack(fill=tk.X, padx=20, pady=5)
        
        detection_check = tk.Checkbutton(options_frame, text="Detección activada", variable=self.detection_var,
                                        command=self.toggle_detection, bg='#3b3b3b', fg='white', 
                                        selectcolor='#2196F3', font=('Arial', 9))
        detection_check.pack(side=tk.LEFT, padx=(0, 20))
        
        save_check = tk.Checkbutton(options_frame, text="Auto-guardar detecciones", variable=self.save_var,
                                   command=self.toggle_save, bg='#3b3b3b', fg='white', 
                                   selectcolor='#4CAF50', font=('Arial', 9))
        save_check.pack(side=tk.LEFT)
        
        # Panel de video
        video_frame = tk.Frame(main_frame, bg='#1e1e1e', relief=tk.SUNKEN, bd=2)
        video_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Label para mostrar video
        self.video_label = tk.Label(video_frame, text="Selecciona una cámara o abre una imagen\npara comenzar", 
                                   bg='#1e1e1e', fg='#888888', font=('Arial', 16))
        self.video_label.pack(expand=True)
        
        # Panel inferior - Estado y detecciones
        info_frame = tk.Frame(main_frame, bg='#3b3b3b', relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X)
        
        # Estado
        status_frame = tk.Frame(info_frame, bg='#3b3b3b')
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(status_frame, text="Estado:", bg='#3b3b3b', fg='white', font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        status_label = tk.Label(status_frame, textvariable=self.status_var, bg='#3b3b3b', fg='#4CAF50', font=('Arial', 9))
        status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Panel de detecciones
        detection_frame = tk.Frame(info_frame, bg='#3b3b3b')
        detection_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(detection_frame, text="Últimas detecciones:", bg='#3b3b3b', fg='white', font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        self.detection_text = tk.Text(detection_frame, height=4, bg='#2b2b2b', fg='#ffffff', 
                                     font=('Courier', 9), relief=tk.FLAT)
        self.detection_text.pack(fill=tk.X, pady=(5, 0))
        
        # Scrollbar para detecciones
        scrollbar = ttk.Scrollbar(self.detection_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.detection_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.detection_text.yview)
    
    def update_status(self, message, color='#4CAF50'):
        """Actualiza el mensaje de estado"""
        self.status_var.set(message)
        # También podríamos cambiar el color aquí si fuera necesario
    
    def add_detection_log(self, text, confidence=None):
        """Añade una detección al log"""
        timestamp = time.strftime("%H:%M:%S")
        if confidence:
            log_entry = f"[{timestamp}] 🚗 {text} (Confianza: {confidence:.2f})\n"
        else:
            log_entry = f"[{timestamp}] 📝 {text}\n"
        
        self.detection_text.insert(tk.END, log_entry)
        self.detection_text.see(tk.END)
        
        # Limitar líneas del log
        lines = self.detection_text.get("1.0", tk.END).split('\n')
        if len(lines) > 50:
            self.detection_text.delete("1.0", "10.0")
    
    def scan_cameras_async(self):
        """Escanea cámaras en un hilo separado"""
        self.update_status("Buscando cámaras...", '#FF9800')
        threading.Thread(target=self.scan_cameras, daemon=True).start()
    
    def scan_cameras(self):
        """Escanea la red en busca de cámaras"""
        try:
            cameras = []
            
            # Cámaras locales
            for i in range(5):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        cameras.append(f"Cámara Local {i}")
                        self.available_cameras.append({'type': 'local', 'index': i, 'name': f"Cámara Local {i}"})
                    cap.release()
            
            # Cámaras IP (versión simplificada para la demo)
            network_base = self.get_local_network()
            common_ips = [f"{network_base}.{i}" for i in [1, 100, 101, 102, 254]]  # IPs comunes
            
            for ip in common_ips:
                if self.quick_ping(ip):
                    # Probar URLs comunes
                    test_urls = [
                        f"http://{ip}/video",
                        f"http://{ip}:8080/video",
                        f"rtsp://{ip}/stream"
                    ]
                    
                    for url in test_urls:
                        if self.test_camera_url(url):
                            camera_name = f"Cámara IP {ip}"
                            cameras.append(camera_name)
                            self.available_cameras.append({'type': 'ip', 'url': url, 'name': camera_name})
                            break
            
            # Actualizar UI en el hilo principal
            self.root.after(0, self.update_camera_list, cameras)
            
        except Exception as e:
            self.root.after(0, self.update_status, f"Error buscando cámaras: {str(e)}", '#f44336')
    
    def get_local_network(self):
        """Obtiene la base de la red local"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return '.'.join(local_ip.split('.')[:-1])
        except:
            return "192.168.1"
    
    def quick_ping(self, ip):
        """Ping rápido para verificar si la IP está activa"""
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], 
                                  capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def test_camera_url(self, url):
        """Prueba rápidamente si una URL de cámara funciona"""
        try:
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                return ret and frame is not None
            return False
        except:
            return False
    
    def update_camera_list(self, cameras):
        """Actualiza la lista de cámaras en la UI"""
        self.camera_combo['values'] = cameras
        if cameras:
            self.camera_combo.current(0)
            self.update_status(f"Encontradas {len(cameras)} cámaras")
        else:
            self.camera_combo.set("No se encontraron cámaras")
            self.update_status("No se encontraron cámaras", '#f44336')
    
    def on_camera_selected(self, event=None):
        """Maneja la selección de cámara"""
        selection = self.camera_combo.current()
        if selection >= 0 and selection < len(self.available_cameras):
            self.current_camera = self.available_cameras[selection]
            self.update_status(f"Cámara seleccionada: {self.current_camera['name']}")
    
    def start_stream(self):
        """Inicia el stream de video"""
        if not self.current_camera:
            messagebox.showwarning("Advertencia", "Selecciona una cámara primero")
            return
        
        try:
            if self.current_camera['type'] == 'local':
                self.cap = cv2.VideoCapture(self.current_camera['index'])
            else:
                self.cap = cv2.VideoCapture(self.current_camera['url'])
            
            if not self.cap.isOpened():
                messagebox.showerror("Error", "No se pudo conectar a la cámara")
                return
            
            self.is_streaming = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.update_status("Transmitiendo...")
            
            self.stream_video()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar stream: {str(e)}")
    
    def stop_stream(self):
        """Detiene el stream de video"""
        self.is_streaming = False
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("Stream detenido")
        
        # Limpiar video label
        self.video_label.config(image='', text="Stream detenido\nSelecciona una cámara para continuar")
    
    def stream_video(self):
        """Loop principal del stream de video"""
        if self.is_streaming and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            if ret:
                # Procesar frame si la detección está activada
                if self.detection_enabled:
                    frame = self.process_frame(frame)
                
                # Convertir y mostrar frame
                self.display_frame(frame)
                
                # Continuar el loop
                self.root.after(30, self.stream_video)  # ~33 FPS
            else:
                self.stop_stream()
                messagebox.showerror("Error", "Perdida la conexión con la cámara")
    
    def process_frame(self, frame):
        """Procesa un frame para detectar placas"""
        try:
            result = self.reader.readtext(frame, paragraph=False, allowlist=self.allowed_chars)
            
            for res in result:
                confidence = res[2]
                text = res[1]
                
                # Filtrar detecciones con baja confianza
                if confidence > 0.5:
                    self.add_detection_log(text, confidence)
                    
                    # Guardar automáticamente si está activado
                    if self.save_var.get():
                        self.save_detection_image(frame, text)
                    
                    # Dibujar rectángulos y texto
                    pts = np.array(res[0], dtype=np.int32)
                    
                    # Rectángulo de fondo para el texto
                    cv2.fillPoly(frame, [pts], (166, 56, 242))
                    
                    # Texto
                    cv2.putText(frame, f"{text} ({confidence:.2f})", 
                              tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    
                    # Rectángulo alrededor
                    cv2.polylines(frame, [pts], True, (166, 56, 242), 3)
                    
                    # Puntos de esquina
                    for i, pt in enumerate(pts):
                        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255)]
                        cv2.circle(frame, tuple(pt), 5, colors[i], -1)
            
        except Exception as e:
            print(f"Error procesando frame: {e}")
        
        return frame
    
    def display_frame(self, frame):
        """Muestra un frame en la interfaz"""
        try:
            # Redimensionar frame para ajustarse a la ventana
            height, width = frame.shape[:2]
            max_width, max_height = 800, 600
            
            if width > max_width or height > max_height:
                scale = min(max_width/width, max_height/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # Convertir de BGR a RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convertir a imagen de PIL y luego a PhotoImage
            image_pil = Image.fromarray(frame_rgb)
            image_tk = ImageTk.PhotoImage(image_pil)
            
            # Mostrar en label
            self.video_label.config(image=image_tk, text='')
            self.video_label.image = image_tk  # Mantener referencia
            
        except Exception as e:
            print(f"Error mostrando frame: {e}")
    
    def capture_image(self):
        """Captura la imagen actual"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                filename = f"captura_{int(time.time())}.jpg"
                cv2.imwrite(filename, frame)
                self.add_detection_log(f"Imagen guardada: {filename}")
                messagebox.showinfo("Éxito", f"Imagen guardada como {filename}")
        else:
            messagebox.showwarning("Advertencia", "No hay stream activo")
    
    def open_image_file(self):
        """Abre y procesa una imagen desde archivo"""
        filetypes = [
            ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tiff"),
            ("Todos los archivos", "*.*")
        ]
        
        filename = filedialog.askopenfilename(title="Seleccionar imagen", filetypes=filetypes)
        
        if filename:
            try:
                image = cv2.imread(filename)
                if image is not None:
                    self.add_detection_log(f"Procesando imagen: {os.path.basename(filename)}")
                    processed_image = self.process_frame(image.copy())
                    self.display_frame(processed_image)
                    self.update_status(f"Imagen cargada: {os.path.basename(filename)}")
                else:
                    messagebox.showerror("Error", "No se pudo cargar la imagen")
            except Exception as e:
                messagebox.showerror("Error", f"Error procesando imagen: {str(e)}")
    
    def save_detection_image(self, frame, text):
        """Guarda automáticamente imágenes con detecciones"""
        try:
            if not os.path.exists("detecciones"):
                os.makedirs("detecciones")
            
            filename = f"detecciones/placa_{text}_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
        except Exception as e:
            print(f"Error guardando detección: {e}")
    
    def toggle_detection(self):
        """Activa/desactiva la detección"""
        self.detection_enabled = self.detection_var.get()
        status = "activada" if self.detection_enabled else "desactivada"
        self.add_detection_log(f"Detección {status}")
    
    def toggle_save(self):
        """Activa/desactiva el guardado automático"""
        self.save_detections = self.save_var.get()
        status = "activado" if self.save_detections else "desactivado"
        self.add_detection_log(f"Auto-guardado {status}")
    
    def run(self):
        """Ejecuta la aplicación"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
    
    def on_closing(self):
        """Maneja el cierre de la aplicación"""
        if self.is_streaming:
            self.stop_stream()
        self.root.quit()
        self.root.destroy()

def main():
    """Función principal"""
    try:
        app = PlateDetectorGUI()
        app.run()
    except Exception as e:
        print(f"Error iniciando aplicación: {e}")

if __name__ == "__main__":
    main()