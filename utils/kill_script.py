import subprocess
import os


def get_pids(port):
    """Obtiene una lista de PIDs de los procesos que están escuchando en un puerto específico."""
    try:
        result = subprocess.check_output(['lsof', '-t', '-i', f':{port}'], text=True)
        pids = result.strip().split('\n')
        return [int(pid) for pid in pids if pid]
    except subprocess.CalledProcessError:
        return []


def kill_processes(pids):
    """Mata los procesos dados sus PIDs."""
    for pid in pids:
        try:
            os.kill(pid, 9)
            print(f"Proceso con PID {pid} ha sido terminado.")
        except OSError as e:
            print(f"No se pudo terminar el proceso con PID {pid}: {e}")


def remove_files():
    """Elimina los archivos de datos del master y los esclavos."""
    files_to_remove = [
        'db/centralized/master_data.json',
        'db/centralized/slave_1_data.json',
        'db/centralized/slave_2_data.json'
    ]

    for file_path in files_to_remove:
        try:
            os.remove(file_path)
            print(f"Archivo {file_path} eliminado.")
        except FileNotFoundError:
            print(f"Archivo {file_path} no encontrado.")
        except OSError as e:
            print(f"No se pudo eliminar el archivo {file_path}: {e}")


def main():
    ports = [32770, 32771, 32772]
    for port in ports:
        print(f"Buscando procesos en el puerto :{port}")
        pids = get_pids(port)
        if pids:
            kill_processes(pids)
        else:
            print(f"No se encontraron procesos en el puerto :{port}")

    remove_files()


if __name__ == "__main__":
    main()
