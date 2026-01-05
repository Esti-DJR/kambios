#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KAMBIOS - CLI version
Versión de consola con vista previa, confirmación y sistema de deshacer.
"""

import os                   # Interactuar con el sistema de archivos
import json                 # Guardar/recuperar el plan de deshacer en formato legible
import sys                  # Acceso a funcionalidades del sistema
from pathlib import Path    # Util para lidiar con rutas del sistema


# Nombre del archivo oculto que guarda la operación para deshacer
# Comienza con punto para que sea "oculto" en Unix/macOS. En Windows no hace nada, pero bueno.
UNDO_FILE = ".kambios_undo.json"

"""
Función principal que controla el flujo del programa.
Usa recursión simple para volver al menú si hay errores porque es lo que sé hacer, ya aprenderemos algo mejor.
"""

def main():

    print("\n=== KAMBIOS - CLI con VISTA PREVIA y DESHACER ===\n")

    # Pedir carpeta al usuario. Si no da ninguna, usar la carpeta actual (os.getcwd())
    folder = input("¿En qué carpeta trabajar? (deja vacío para usar la actual): ").strip()
    if not folder:
        folder = os.getcwd()  # Devuelve la ruta absoluta de la carpeta de trabajo actual
    else:
        # Validar que la carpeta exista
        if not os.path.isdir(folder):
            print(f"❌ Error: La carpeta '{folder}' no existe.")
            return  # Salir si no es válida

    # Construir ruta completa al archivo de deshacer dentro de la carpeta seleccionada
    undo_path = os.path.join(folder, UNDO_FILE)

    # Si existe un archivo de deshacer, ofrecer deshacer antes de hacer algo nuevo
    if os.path.exists(undo_path):
        print(f"\n⚠️  Se detectó una operación anterior que se puede deshacer.")
        choice = input("¿Quieres deshacerla ahora? (s/n): ").strip().lower()
        if choice in ("s", "si", "y", "yes"):
            undo_last_rename(folder, undo_path)
            return

    # Mostramos un menú de acciones
    print("\n¿Qué quieres hacer?")
    print("1) Numerar archivos")
    print("2) Reemplazar nombre completo")
    print("3) Reemplazar parte del nombre")
    print("4) Salir")

    action = input("\nElige una opción (1-4): ").strip()

    # Llamar a la función correspondiente según la elección
    if action == "1":
        number_preview(folder)
    elif action == "2":
        full_replace_preview(folder)
    elif action == "3":
        part_replace_preview(folder)
    elif action == "4":
        print("👋 ¡Hasta luego!")
        return
    else:
        print("❌ Opción inválida.")
        main()  # Recursión si la opción no es válida, seguro que hay una forma mejor de hacer esto.


def list_files(folder):
    """
    Devuelve una lista de archivos (no carpetas) en la carpeta dada.
    Usa comprensión de listas + os.path.isfile para filtrar (por cada cosa en la carpeta, si es un archivo, devuélvelo a main).
    """
    return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]


def show_preview(changes):
    """
    Muestra una vista previa de los cambios y pide confirmación.
    Devuelve True si el usuario confirma, False si... si no.
    También verifica duplicados, si dos archivos terminan con el mismo nombre, se aborta.
    """
    if not changes:
        print("🔍 No se encontraron cambios que aplicar.")
        return False

    print("\n📄 VISTA PREVIA DE CAMBIOS:")
    print("-" * 50)
    for old, new in changes:
        print(f"  {old}  →  {new}")
    print("-" * 50)

    # Evitar la sobrescritura por nombres duplicados y abortar.
    new_names = [new for _, new in changes]
    if len(new_names) != len(set(new_names)):
        print("\n❌ ¡ERROR! Los nombres nuevos generan duplicados. Abortando.")
        return False
    # ¿Seguuuuro?
    confirm = input(f"\n¿Aplicar estos {len(changes)} cambios? (s/n): ").strip().lower()
    return confirm in ("s", "si", "y", "yes")


def save_undo_file(folder, changes):
    """
    Guarda el plan inverso (para deshacer) en un archivo JSON dentro de la carpeta.
    El plan de deshacer es: [(nuevo_nombre, nombre_original), ...]
    """
    undo_path = os.path.join(folder, UNDO_FILE)
    undo_plan = [[new, old] for old, new in changes]  # Invertimos el orden.
    with open(undo_path, "w", encoding="utf-8") as f:
        # json.dump() traduce la serie a JSON.
        json.dump({
            "source": "kambios_cli",  # ¿De dónde viene el json? (Por si hay errores o algo.)
            "renames": undo_plan
        }, f, indent=2, ensure_ascii=False)  # indent=2 para que se lea facilito.


def apply_changes(folder, changes):
    """
    Aplica los renombres y guarda el archivo de deshacer.
    Usa try/except para no romper el programa si falla un renombre.
    """
    try:
        for old_name, new_name in changes:
            src = os.path.join(folder, old_name)  # Ruta completa del archivo original.
            dst = os.path.join(folder, new_name)  # Ruta completa del nuevo nombre.
            os.rename(src, dst)  # rename hace el cambio de src a dst.
        print(f"\n✅ ¡{len(changes)} archivos renombrados correctamente!")
        save_undo_file(folder, changes)
        print("↩️  Puedes deshacer esta operación la próxima vez que abras esta carpeta.")
    except Exception as e:
        # Manejo genérico de errores, si pasa algo malo, sea lo que sea, debería decirlo aquí.
        print(f"\n❌ Error al renombrar: {e}")


# --- Funciones de acción con vista previa ---

def number_preview(folder):
    # Función para numerar archivos 0 - documento.pdf, 1 - documento.pdf,... Este es útil para, por ejemplo, libros en varios PDFs numerados, o para una carpeta de fotos de un viaje o algo así.
    files = list_files(folder)
    if not files:
        print("📁 La carpeta está vacía.")
        return

    print(f"\nArchivos en '{folder}': {', '.join(files)}")
    text = input("Texto después del número: ").strip()
    if not text:
        print("❌ El texto no puede estar vacío.")
        return

    # Generar lista de cambios: (nombre_actual, nombre_propuesto).
    changes = []
    for i, filename in enumerate(files):
        name, ext = os.path.splitext(filename)  # Separa "foto.jpg" en "foto" y ".jpg", porque lo que queremos cambiar es el nombre, no la extensión (a lo mejor algún día).
        new_name = f"{i} - {text}{ext}"
        if filename != new_name:  # Evitar renombrar si no hay cambio.
            changes.append((filename, new_name))

    if show_preview(changes):
        apply_changes(folder, changes)


def full_replace_preview(folder):
    # Función para reemplazar todos los nombres por uno mismo base, útil para películas que tienen archivos de subs que se tienen que llamar igual.
    files = list_files(folder)
    if not files:
        print("📁 La carpeta está vacía.")
        return

    print(f"\nArchivos en '{folder}': {', '.join(files)}")
    text = input("Nuevo nombre base: ").strip()
    if not text:
        print("❌ El nombre no puede estar vacío.")
        return

    changes = []
    for filename in files:
        _, ext = os.path.splitext(filename)
        new_name = f"{text}{ext}"
        if filename != new_name:
            changes.append((filename, new_name))

    if show_preview(changes):
        apply_changes(folder, changes)


def part_replace_preview(folder):
    # Función para reemplazar parte del nombre de todos los archivos, muy útil para sanear una lista de roms, por ejemplo, eliminando partes que sobran del nombre del juego.
    files = list_files(folder)
    if not files:
        print("📁 La carpeta está vacía.")
        return

    print(f"\nArchivos en '{folder}': {', '.join(files)}")
    text_remove = input("Texto a quitar: ")
    if not text_remove:
        print("❌ Debes ingresar texto a quitar.")
        return
    text_replace = input("Texto a poner (puede estar vacío): ")

    changes = []
    for filename in files:
        if text_remove in filename:  # Solo si el texto está presente.
            new_name = filename.replace(text_remove, text_replace)
            if filename != new_name:
                changes.append((filename, new_name))

    if show_preview(changes):
        apply_changes(folder, changes)


def undo_last_rename(folder, undo_path):
    # Lee el archivo de deshacer y revierte los cambios. Renombra cada archivo del "nuevo nombre" al "original".
    try:
        with open(undo_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # carga el JSON en la variable data.
        renames = data.get("renames", [])

        if not renames:
            print("❌ El archivo de deshacer está vacío.")
            return

        print(f"\n🔄 Deshaciendo {len(renames)} cambios:")
        for current, original in renames:
            src = os.path.join(folder, current)
            dst = os.path.join(folder, original)
            if os.path.exists(src):
                os.rename(src, dst)
                print(f"  {current} → {original}")
            else:
                print(f"  ⚠️  {current} no encontrado (quizás ya fue movido).")

        # Eliminar archivo de deshacer tras usarlo.
        os.remove(undo_path)
        print("\n✅ ¡Operación deshecha! El archivo de deshacer ha sido eliminado.")
    except Exception as e:
        print(f"❌ Error al deshacer: {e}")


# --- Punto de entrada del programa ---
if __name__ == "__main__":
    # Al parecer es convención empezar los archivos Python así, así que eso hice.
    try:
        main()
    except KeyboardInterrupt:
        # Captura Ctrl+C y muestra mensaje si lo usa el usuario.
        print("\n\n🛑 Terminado por el usuario.")
    except Exception as e:
        # Captura cualquier otro error inesperado y lo tira a la terminal.
        print(f"\n💥 Error inesperado: {e}")

