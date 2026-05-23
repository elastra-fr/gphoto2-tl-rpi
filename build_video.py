#!/usr/bin/env python3
"""
Assemblage d'un timelapse en vidéo à partir d'un dossier de photos.
Usage : python3 build_video.py [dossier_session] [--fps 24]
         Si aucun dossier n'est fourni, liste les sessions disponibles.
"""
import subprocess
import os
import sys
import argparse
import socket
import shutil


def get_base_path():
    hostname = socket.gethostname()
    if "raspberry" in hostname.lower() or os.path.exists("/proc/device-tree/model"):
        return "/home/pi/partage"
    else:
        uid = os.getuid()
        run_user = f"/run/user/{uid}"
        # Cherche le point de montage kio-fuse (suffixe aléatoire)
        for entry in os.listdir(run_user):
            if entry.startswith("kio-fuse-"):
                candidate = os.path.join(run_user, entry, "smb", "rpi.local", "partage")
                if os.path.isdir(candidate):
                    return candidate
        return os.path.join(run_user, "kio-fuse", "smb", "rpi.local", "partage")


def pick_session(base_path):
    if not os.path.isdir(base_path):
        print(f"❌ Dossier de base introuvable : {base_path}")
        sys.exit(1)

    sessions = sorted([
        d for d in os.listdir(base_path)
        if d.startswith("timelapse_") and os.path.isdir(os.path.join(base_path, d))
    ])

    if not sessions:
        print(f"❌ Aucune session trouvée dans {base_path}")
        sys.exit(1)

    print(f"📁 Sessions disponibles dans {base_path} :\n")
    for i, s in enumerate(sessions):
        nb = len([f for f in os.listdir(os.path.join(base_path, s)) if f.endswith(".jpg")])
        print(f"  [{i + 1}] {s}  ({nb} photos)")

    print()
    try:
        choix = int(input("Choisir une session (numéro) : ")) - 1
        if not 0 <= choix < len(sessions):
            raise ValueError
    except ValueError:
        print("❌ Choix invalide.")
        sys.exit(1)

    return os.path.join(base_path, sessions[choix])


def build_video(session_path, fps):
    session_name = os.path.basename(session_path.rstrip("/"))
    photos = sorted([f for f in os.listdir(session_path) if f.endswith(".jpg")])
    if not photos:
        print(f"❌ Aucune photo trouvée dans {session_path}")
        sys.exit(1)

    print(f"🎬 {len(photos)} photos trouvées — assemblage à {fps} fps...")

    # Détecte le dossier local "Vidéos" (XDG), fallback ~/Videos, ~/Vidéos, puis ./video
    def get_local_video_dir():
        # Try XDG user dirs config
        config = os.path.expanduser("~/.config/user-dirs.dirs")
        if os.path.exists(config):
            try:
                with open(config, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("XDG_VIDEOS_DIR"):
                            _, val = line.split("=", 1)
                            val = val.strip().strip('"')
                            val = val.replace("$HOME", os.path.expanduser("~"))
                            return os.path.abspath(os.path.expanduser(val))
            except Exception:
                pass

        # Common fallbacks
        fallbacks = [os.path.expanduser("~/Videos"), os.path.expanduser("~/Vidéos")]
        for c in fallbacks:
            try:
                os.makedirs(c, exist_ok=True)
                return c
            except Exception:
                continue

        # Final fallback: video/ next to script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_dir = os.path.join(script_dir, "video")
        os.makedirs(local_dir, exist_ok=True)
        return local_dir

    local_dir = get_local_video_dir()
    local_output = os.path.join(local_dir, f"{session_name}.mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", os.path.join(session_path, "photo_*.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        local_output
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Erreur ffmpeg :\n{result.stderr}")
        sys.exit(1)

    print(f"✅ Vidéo créée localement : {local_output}")
    return local_output


def main():
    parser = argparse.ArgumentParser(description="Assemble un timelapse en vidéo MP4.")
    parser.add_argument("session_path", nargs="?", help="Chemin du dossier de session (optionnel)")
    parser.add_argument("--fps", type=float, default=24, help="Fréquence d'images (défaut : 24)")
    parser.add_argument("--copy", action="store_true", help="Copier la vidéo vers le partage après création (par défaut: non)")
    args = parser.parse_args()

    if args.session_path:
        session_path = os.path.expanduser(args.session_path)
    else:
        session_path = pick_session(get_base_path())

    if not os.path.isdir(session_path):
        print(f"❌ Dossier introuvable : {session_path}")
        sys.exit(1)

    local_output = build_video(session_path, args.fps)

    if args.copy:
        session_name = os.path.basename(session_path.rstrip("/"))
        remote_output = os.path.join(session_path, f"{session_name}.mp4")
        try:
            shutil.copy2(local_output, remote_output)
            print(f"✅ Vidéo copiée vers le partage : {remote_output}")
        except Exception as e:
            print(f"⚠️  Erreur lors de la copie vers le partage : {e}")
            print(f"✅ La vidéo reste disponible localement : {local_output}")


if __name__ == "__main__":
    main()
