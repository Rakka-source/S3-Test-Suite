import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from botocore.exceptions import ClientError

from aws import AWSValidator, S3Manager
from config import cargar_configuracion


class AppS3:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gestor AWS S3 Modular")
        self.root.geometry("700x780")

        self.configuraciones: dict = {}
        self.s3_manager: S3Manager | None = None
        self.perfil_actual: str | None = None

        self._cargar_configuracion()
        self._construir_interfaz()

    def _cargar_configuracion(self):
        try:
            self.configuraciones = cargar_configuracion()
        except FileNotFoundError:
            messagebox.showwarning(
                "Atención",
                "No se encontró config_s3.json. Crea el archivo según las instrucciones.",
            )
            self.configuraciones = {}

    def _construir_interfaz(self):
        self._crear_seccion_perfil()
        self._crear_seccion_exploracion()
        self._crear_seccion_archivos()
        self._crear_seccion_carpetas()
        self._crear_seccion_validacion()
        self._crear_seccion_log()

    def _crear_seccion_perfil(self):
        frame = ttk.LabelFrame(self.root, text=" 1. Entorno de AWS ", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="Selecciona Configuración:").pack(side="left", padx=5)
        self.cmbx_perfil = ttk.Combobox(
            frame,
            values=list(self.configuraciones.keys()),
            width=40,
            state="readonly",
        )
        self.cmbx_perfil.pack(side="left", padx=5)
        self.cmbx_perfil.bind("<<ComboboxSelected>>", self._al_seleccionar_perfil)

    def _crear_seccion_exploracion(self):
        frame = ttk.LabelFrame(self.root, text=" 2. Exploración ", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(frame, text="Probar Conexión", command=self._btn_probar).grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Button(frame, text="Listar Todo (Raíz)", command=lambda: self._btn_listar("")).grid(
            row=0, column=1, padx=5, pady=5
        )

        ttk.Label(frame, text="Carpeta (opcional):").grid(row=1, column=0, sticky="e", padx=5)
        self.ent_prefijo = ttk.Entry(frame, width=30)
        self.ent_prefijo.grid(row=1, column=1, padx=5)
        ttk.Button(
            frame,
            text="Listar Carpeta",
            command=lambda: self._btn_listar(self.ent_prefijo.get()),
        ).grid(row=1, column=2, padx=5)

    def _crear_seccion_archivos(self):
        frame = ttk.LabelFrame(self.root, text=" 3. Gestión de Archivos ", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="Carpeta destino (opcional):").grid(
            row=0, column=0, sticky="e", padx=5, pady=5
        )
        self.ent_carpeta_destino = ttk.Entry(frame, width=30)
        self.ent_carpeta_destino.grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Subir Archivo", command=self._btn_subir).grid(
            row=0, column=2, padx=5, pady=5
        )

        ttk.Label(frame, text="Nombre S3 a eliminar:").grid(
            row=1, column=0, sticky="e", padx=5, pady=10
        )
        self.ent_eliminar = ttk.Entry(frame, width=30)
        self.ent_eliminar.grid(row=1, column=1, padx=5)
        ttk.Button(frame, text="Eliminar Archivo", command=self._btn_eliminar).grid(
            row=1, column=2, padx=5
        )

    def _crear_seccion_carpetas(self):
        frame = ttk.LabelFrame(self.root, text=" 4. Gestión de Carpetas ", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="Nombre de carpeta:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.ent_carpeta = ttk.Entry(frame, width=30)
        self.ent_carpeta.grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Crear Carpeta", command=self._btn_crear_carpeta).grid(
            row=0, column=2, padx=5, pady=5
        )
        ttk.Button(frame, text="Eliminar Carpeta", command=self._btn_eliminar_carpeta).grid(
            row=0, column=3, padx=5, pady=5
        )

    def _crear_seccion_validacion(self):
        frame = ttk.LabelFrame(self.root, text=" 5. Validación de Permisos ", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            frame,
            text="Ejecuta pruebas de Cognito, lectura, escritura, multipart y eliminación.",
            wraplength=620,
        ).pack(anchor="w", padx=5, pady=(0, 5))
        ttk.Button(frame, text="Ejecutar Auditoría de Permisos", command=self._btn_validar).pack(
            anchor="w", padx=5, pady=5
        )

    def _crear_seccion_log(self):
        frame = ttk.LabelFrame(self.root, text=" Consola de Salida ", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.txt_log = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=12)
        self.txt_log.pack(fill="both", expand=True)

    def log(self, mensaje: str):
        self.txt_log.insert(tk.END, mensaje + "\n")
        self.txt_log.see(tk.END)
        self.root.update()

    def _procesar_error(self, error: Exception):
        if isinstance(error, ClientError):
            codigo = error.response["Error"]["Code"]
            mensaje = error.response["Error"]["Message"]
            self.log(f"❌ Error de AWS ({codigo}): {mensaje}")
        else:
            self.log(f"❌ Error interno: {error}")

    def _al_seleccionar_perfil(self, _event=None):
        perfil = self.cmbx_perfil.get()
        config = self.configuraciones[perfil]
        self.perfil_actual = perfil
        try:
            self.s3_manager = S3Manager(config)
            self.log(f"\n--- 🔄 Entorno cargado: {perfil} ---")
            self.log(
                f"Bucket Objetivo: {config.get('NOMBRE_BUCKET', config.get('bucket_name'))} "
                f"| Región: {config.get('REGION', config.get('region_name'))}"
            )
        except Exception as exc:
            self._procesar_error(exc)

    def _validar_perfil(self) -> bool:
        if not self.perfil_actual:
            messagebox.showwarning("Atención", "Primero selecciona un entorno en el menú desplegable.")
            return False
        return True

    def _validar_manager(self) -> bool:
        if not self._validar_perfil() or not self.s3_manager:
            messagebox.showwarning("Atención", "No se pudo inicializar el cliente S3 para este perfil.")
            return False
        return True

    def _btn_probar(self):
        if not self._validar_manager():
            return
        try:
            self.log("Probando conexión...")
            self.log(self.s3_manager.probar_acceso())
        except Exception as exc:
            self._procesar_error(exc)

    def _btn_listar(self, prefijo: str):
        if not self._validar_manager():
            return
        try:
            etiqueta = prefijo if prefijo else "raíz"
            self.log(f"Listando archivos en '{etiqueta}'...")
            self.log(self.s3_manager.listar_archivos(prefijo))
        except Exception as exc:
            self._procesar_error(exc)

    def _btn_subir(self):
        if not self._validar_manager():
            return

        ruta_archivo = filedialog.askopenfilename(title="Selecciona un archivo")
        if not ruta_archivo:
            return

        carpeta_destino = self.ent_carpeta_destino.get().strip()
        publico = messagebox.askyesno(
            "Permisos",
            "¿Quieres que el archivo sea PÚBLICO para todo el mundo?\n\n"
            "(No = Generará URL privada de 1 hora)",
        )

        try:
            nombre = os.path.basename(ruta_archivo)
            ruta_visual = f"{carpeta_destino}/{nombre}" if carpeta_destino else nombre
            self.log(f"Subiendo {ruta_visual}...")
            self.log(self.s3_manager.subir_archivo(ruta_archivo, carpeta=carpeta_destino, publico=publico))
        except Exception as exc:
            self._procesar_error(exc)

    def _btn_eliminar(self):
        if not self._validar_manager():
            return

        key_s3 = self.ent_eliminar.get().strip()
        if not key_s3:
            messagebox.showwarning("Atención", "Escribe el nombre/ruta del archivo en S3 que quieres eliminar.")
            return

        if messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar '{key_s3}' del bucket?"):
            try:
                self.log(f"Eliminando '{key_s3}'...")
                self.log(self.s3_manager.eliminar_archivo(key_s3))
            except Exception as exc:
                self._procesar_error(exc)

    def _btn_crear_carpeta(self):
        if not self._validar_manager():
            return

        nombre_carpeta = self.ent_carpeta.get().strip()
        if not nombre_carpeta:
            messagebox.showwarning("Atención", "Escribe el nombre de la carpeta que quieres crear.")
            return

        try:
            self.log(f"Creando carpeta '{nombre_carpeta}'...")
            self.log(self.s3_manager.crear_carpeta(nombre_carpeta))
        except Exception as exc:
            self._procesar_error(exc)

    def _btn_eliminar_carpeta(self):
        if not self._validar_manager():
            return

        nombre_carpeta = self.ent_carpeta.get().strip()
        if not nombre_carpeta:
            messagebox.showwarning("Atención", "Escribe el nombre de la carpeta que quieres eliminar.")
            return

        prefijo = nombre_carpeta.strip("/") + "/"
        if messagebox.askyesno(
            "Confirmar",
            f"¿Eliminar la carpeta '{prefijo}' y todo su contenido del bucket?",
        ):
            try:
                self.log(f"Eliminando carpeta '{prefijo}'...")
                self.log(self.s3_manager.eliminar_carpeta(nombre_carpeta))
            except Exception as exc:
                self._procesar_error(exc)

    def _btn_validar(self):
        if not self._validar_perfil():
            return

        config = self.configuraciones[self.perfil_actual]
        try:
            self.log("\nIniciando auditoría de permisos...")
            validator = AWSValidator(config)
            resultados = validator.ejecutar_auditoria()
            self.log(validator.formatear_informe(resultados))
        except Exception as exc:
            self._procesar_error(exc)
