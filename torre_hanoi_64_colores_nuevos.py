import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox


# ----------------------------------------------------------------------
# Lógica del juego
# ----------------------------------------------------------------------
class TorreHanoi:
    """Torre de Hanoi con tres torres representadas como listas (pilas)."""

    def __init__(self, n_discos):
        self.n = n_discos
        self.torres = {"A": list(range(n_discos, 0, -1)), "B": [], "C": []}
        self.movimientos = 0

    def mover_disco(self, origen, destino):
        """Mueve el disco superior de una torre a otra."""
        self.torres[destino].append(self.torres[origen].pop())
        self.movimientos += 1

    def resolver(self, n, origen, destino, auxiliar):
        """Algoritmo recursivo clásico (usado para medir tiempos)."""
        if n == 0:
            return
        self.resolver(n - 1, origen, auxiliar, destino)
        self.mover_disco(origen, destino)
        self.resolver(n - 1, auxiliar, destino, origen)

    def generar_movimientos(self, n, origen, destino, auxiliar):
        """Versión generadora: produce (origen, destino) paso a paso
        para poder animar cada movimiento en la interfaz."""
        if n == 0:
            return
        yield from self.generar_movimientos(n - 1, origen, auxiliar, destino)
        yield (origen, destino)
        yield from self.generar_movimientos(n - 1, auxiliar, destino, origen)

    def movimientos_minimos(self):
        """Número mínimo de movimientos teóricos: 2^n - 1."""
        return 2 ** self.n - 1


def medir(n):
    juego = TorreHanoi(n)
    inicio = time.perf_counter()
    juego.resolver(n, "A", "C", "B")
    fin = time.perf_counter()
    assert juego.movimientos == juego.movimientos_minimos()
    return juego.movimientos, fin - inicio


def formatear_tiempo(segundos):
    if segundos < 60:
        return f"{segundos:.6f} s"
    if segundos < 3600 * 24 * 365:
        return f"{segundos:,.1f} s ({segundos / 60:,.1f} min)"
    return f"{segundos:.3e} s (≈ {segundos / (3600 * 24 * 365):,.0f} años)"


# ----------------------------------------------------------------------
# Interfaz gráfica
# ----------------------------------------------------------------------
class HanoiGUI(tk.Tk):
    ANCHO, ALTO = 760, 360
    X_TORRES = {"A": 140, "B": 380, "C": 620}
    Y_BASE = 330
    MIN_DISCOS = 30
    MAX_DISCOS = 64
    ESPACIO_VERTICAL = 290  # píxeles disponibles para apilar discos

    def __init__(self):
        super().__init__()
        self.title("Torre de Hanoi (30 a 64 discos)")
        self.resizable(False, False)

        self.juego = None
        self.generador = None
        self.animando = False
        self.pausado = False
        self.alto_disco = 4
        self.cola = queue.Queue()

        self._crear_widgets()
        self.reiniciar()
        self.after(100, self._revisar_cola)

    # ---------- construcción de la ventana ----------
    def _crear_widgets(self):
        barra = ttk.Frame(self, padding=8)
        barra.pack(fill="x")

        ttk.Label(barra, text="Discos (30-64):").pack(side="left")
        self.var_discos = tk.IntVar(value=self.MIN_DISCOS)
        self.spin = ttk.Spinbox(barra, from_=self.MIN_DISCOS,
                                to=self.MAX_DISCOS, width=4,
                                textvariable=self.var_discos,
                                command=self.reiniciar)
        self.spin.pack(side="left", padx=(4, 12))
        self.spin.bind("<Return>", lambda e: self.reiniciar())

        ttk.Label(barra, text="Velocidad:").pack(side="left")
        self.var_vel = tk.IntVar(value=100)
        ttk.Scale(barra, from_=500, to=1, variable=self.var_vel,
                  length=100).pack(side="left", padx=(4, 12))

        self.btn_resolver = ttk.Button(barra, text="Resolver",
                                       command=self.resolver)
        self.btn_resolver.pack(side="left", padx=2)
        self.btn_pausa = ttk.Button(barra, text="Pausar",
                                    command=self.alternar_pausa)
        self.btn_pausa.pack(side="left", padx=2)
        ttk.Button(barra, text="Reiniciar",
                   command=self.reiniciar).pack(side="left", padx=2)
        self.btn_medir = ttk.Button(barra, text="Medir tiempos",
                                    command=self.medir_tiempos)
        self.btn_medir.pack(side="left", padx=2)

        self.canvas = tk.Canvas(self, width=self.ANCHO, height=self.ALTO,
                                bg="#0f172a", highlightthickness=0)
        self.canvas.pack()

        self.var_estado = tk.StringVar()
        ttk.Label(self, textvariable=self.var_estado,
                  padding=(8, 4)).pack(fill="x")

        cols = ("discos", "movimientos", "tiempo")
        self.tabla = ttk.Treeview(self, columns=cols, show="headings",
                                  height=4)
        self.tabla.heading("discos", text="Discos")
        self.tabla.heading("movimientos", text="Movimientos")
        self.tabla.heading("tiempo", text="Tiempo")
        self.tabla.column("discos", width=80, anchor="center")
        self.tabla.column("movimientos", width=250, anchor="center")
        self.tabla.column("tiempo", width=400, anchor="center")
        self.tabla.pack(fill="x", padx=8, pady=(0, 8))

    # ---------- dibujo ----------
    def dibujar(self):
        c = self.canvas
        c.delete("all")
        n = self.juego.n
        h = self.alto_disco
        c.create_rectangle(20, self.Y_BASE, self.ANCHO - 20,
                           self.Y_BASE + 8, fill="#334155", outline="")
        alto_poste = h * (n + 1) + 6
        for nombre, x in self.X_TORRES.items():
            c.create_rectangle(x - 3, self.Y_BASE - alto_poste, x + 3,
                               self.Y_BASE, fill="#94a3b8", outline="")
            c.create_text(x, self.Y_BASE + 22, text=nombre,
                          font=("Arial", 12, "bold"), fill="#f8fafc")

        max_ancho, min_ancho = 200, 12
        for nombre, torre in self.juego.torres.items():
            x = self.X_TORRES[nombre]
            for nivel, disco in enumerate(torre):
                ancho = min_ancho + (max_ancho - min_ancho) * (disco - 1) / (n - 1)
                y2 = self.Y_BASE - nivel * h
                y1 = y2 - h + 1
                # color en degradado según el tamaño del disco
                tono = int(360 * (disco - 1) / n)
                c.create_rectangle(x - ancho / 2, y1, x + ancho / 2, y2,
                                   fill=self._color(tono), outline="")

    @staticmethod
    def _color(tono):
        """Genera un degradado moderno de turquesa a morado."""
        import colorsys
        # El tono se recibe entre 0 y 360; lo convertimos a 0.48-0.78
        proporcion = max(0, min(1, tono / 360))
        matiz = 0.48 + (0.30 * proporcion)
        r, g, b = colorsys.hsv_to_rgb(matiz, 0.72, 0.96)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    # ---------- acciones ----------
    def reiniciar(self):
        self.animando = False
        self.pausado = False
        self.btn_pausa.config(text="Pausar")
        self.btn_resolver.config(state="normal")
        try:
            n = int(self.var_discos.get())
        except (tk.TclError, ValueError):
            n = self.MIN_DISCOS
        n = max(self.MIN_DISCOS, min(self.MAX_DISCOS, n))
        self.var_discos.set(n)
        self.alto_disco = max(3, self.ESPACIO_VERTICAL // (n + 1))
        self.juego = TorreHanoi(n)
        self.generador = None
        self.dibujar()
        self.var_estado.set(
            f"{n} discos | Movimientos mínimos: "
            f"{self.juego.movimientos_minimos():,} "
            f"(la animación no alcanzará a terminar)")

    def resolver(self):
        if self.animando:
            return
        self.reiniciar()
        n = self.juego.n
        self.generador = self.juego.generar_movimientos(n, "A", "C", "B")
        self.animando = True
        self.btn_resolver.config(state="disabled")
        self.inicio_anim = time.perf_counter()
        self._paso()

    def _paso(self):
        if not self.animando:
            return
        if self.pausado:
            self.after(100, self._paso)
            return
        try:
            origen, destino = next(self.generador)
        except StopIteration:
            self.animando = False
            self.var_estado.set(f"¡Resuelto! {self.juego.movimientos:,} movimientos")
            self.btn_resolver.config(state="normal")
            return
        self.juego.mover_disco(origen, destino)
        self.dibujar()
        total = self.juego.movimientos_minimos()
        pct = 100 * self.juego.movimientos / total
        self.var_estado.set(
            f"Movimiento {self.juego.movimientos:,} de {total:,} "
            f"({pct:.2e} %): {origen} → {destino}")
        self.after(max(1, int(self.var_vel.get())), self._paso)

    def alternar_pausa(self):
        self.pausado = not self.pausado
        self.btn_pausa.config(text="Continuar" if self.pausado else "Pausar")

    # ---------- medición de tiempos (hilo aparte) ----------
    def medir_tiempos(self):
        n_sel = int(self.var_discos.get())
        if not messagebox.askyesno(
                "Medir tiempos",
                "Se medirá REALMENTE 30 discos (≈ 3-4 min según el equipo).\n"
                f"Para {n_sel} y 64 discos el tiempo se ESTIMA con ese ritmo, "
                "porque ejecutarlos es imposible.\n\n¿Continuar?"):
            return
        self.btn_medir.config(state="disabled")
        self.tabla.delete(*self.tabla.get_children())
        threading.Thread(target=self._trabajo_medicion, args=(n_sel,),
                         daemon=True).start()

    def _trabajo_medicion(self, n_sel):
        sys.setrecursionlimit(10000)
        self.cola.put(("estado", "Midiendo 30 discos (tarda varios minutos)..."))
        mov, t = medir(30)
        t_por_mov = t / mov
        self.cola.put(("fila", (30, f"{mov:,}", "REAL: " + formatear_tiempo(t))))
        for n in sorted({n_sel, 64}):
            if n == 30:
                continue
            m = 2 ** n - 1
            self.cola.put(("fila", (n, f"{m:,}",
                                    "ESTIMADO: " + formatear_tiempo(t_por_mov * m))))
        self.cola.put(("fin", None))

    def _revisar_cola(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "estado":
                    self.var_estado.set(dato)
                elif tipo == "fila":
                    self.tabla.insert("", "end", values=dato)
                elif tipo == "fin":
                    self.var_estado.set("Medición terminada.")
                    self.btn_medir.config(state="normal")
        except queue.Empty:
            pass
        self.after(100, self._revisar_cola)


if __name__ == "__main__":
    HanoiGUI().mainloop()
