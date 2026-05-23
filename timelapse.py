#!/usr/bin/env python3
import subprocess
import time
import os
from datetime import datetime

# Détection automatique du système
import platform
import socket

def detect_platform():
    hostname = socket.gethostname()
    if "raspberry" in hostname.lower() or os.path.exists("/proc/device-tree/model"):
        return "rpi"
    else:
        return "linux"

def get_save_path(platform):
    if platform == "rpi":
        return "/home/pi/partage"
    else:
        # Dossier monté en SSHFS sur le PC
        return os.path.expanduser("~/rpi/home/pi/partage")

def take_photo(save_path, index):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{timestamp}_{index:04d}.jpg"
    filepath = os.path.join(save_path, filename)

    cmd = [
        "gphoto2",
        "--capture-image-and-download",
        f"--filename={filepath}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ Photo {index} enregistrée : {filename}")
    else:
        print(f"❌ Erreur photo {index} : {result.stderr}")

    return result.returncode == 0

def main():
    print("=== Timelapse gphoto2 ===\n")

    # Entrées utilisateur
    try:
        intervalle = float(input("Intervalle entre les photos (secondes) : "))
        duree = float(input("Durée totale de la prise (minutes) : "))
    except ValueError:
        print("❌ Valeur invalide.")
        return

    duree_secondes = duree * 60
    nb_photos = int(duree_secondes / intervalle)

    # Détection plateforme
    plateforme = detect_platform()
    save_path = get_save_path(plateforme)

    print(f"\n📍 Plateforme détectée : {plateforme}")
    print(f"📁 Dossier de sauvegarde : {save_path}")
    print(f"📸 Nombre de photos prévues : {nb_photos}")
    print(f"⏱  Intervalle : {intervalle}s | Durée : {duree} min\n")

    # Vérification dossier
    if not os.path.exists(save_path):
        print(f"❌ Dossier introuvable : {save_path}")
        return

    # Vérification gphoto2
    check = subprocess.run(["gphoto2", "--auto-detect"], capture_output=True, text=True)
    if check.returncode != 0 or "usb:" not in check.stdout.lower():
        print("❌ Aucun appareil photo détecté par gphoto2.")
        print(check.stdout)
        return

    print("📷 Appareil détecté :")
    print(check.stdout)

    input("Appuie sur Entrée pour démarrer...\n")

    # Boucle de capture
    start_time = time.time()
    index = 1

    try:
        while time.time() - start_time < duree_secondes:
            take_photo(save_path, index)
            index += 1

            elapsed = time.time() - start_time
            remaining = duree_secondes - elapsed
            print(f"⏳ Temps restant : {remaining:.0f}s\n")

            if remaining > intervalle:
                time.sleep(intervalle)
            else:
                break

    except KeyboardInterrupt:
        print("\n⛔ Arrêt manuel.")

    print(f"\n✅ Terminé — {index - 1} photos prises dans {save_path}")

if __name__ == "__main__":
    main()