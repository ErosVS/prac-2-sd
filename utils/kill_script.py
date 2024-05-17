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


def main():
    ports = [32770, 32771, 32772]
    for port in ports:
        print(f"Buscando procesos en el puerto :{port}")
        pids = get_pids(port)
        if pids:
            kill_processes(pids)
        else:
            print(f"No se encontraron procesos en el puerto :{port}")


if __name__ == "__main__":
    main()
