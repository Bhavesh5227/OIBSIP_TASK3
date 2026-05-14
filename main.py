import sys
import subprocess
from config.settings import HOST, PORT_BASIC, PORT_MAIN


def menu():
    print("\n╔══════════════════════════╗")
    print("║        PyChat 💬         ║")
    print("╠══════════════════════════╣")
    print(f"║  Basic server : {HOST}:{PORT_BASIC}  ║")
    print(f"║  Main  server : {HOST}:{PORT_MAIN}  ║")
    print("╠══════════════════════════╣")
    print("║  1. Start basic server   ║")
    print("║  2. Start basic client   ║")
    print("║  3. Start main  server   ║")
    print("║  4. Start main  client   ║")
    print("║  5. Exit                 ║")
    print("╚══════════════════════════╝")
    return input("Choose: ").strip()


def main():
    while True:
        choice = menu()
        if choice == "1":
            subprocess.run([sys.executable, "server/server_basic.py"])
        elif choice == "2":
            subprocess.run([sys.executable, "client/client_basic.py"])
        elif choice == "3":
            subprocess.run([sys.executable, "server/server_main.py"])
        elif choice == "4":
            subprocess.run([sys.executable, "client/client_main.py"])
        elif choice == "5":
            print("Bye.")
            break
        else:
            print("Invalid choice — enter 1 to 5.")


if __name__ == "__main__":
    main()