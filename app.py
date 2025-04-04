from flask import Flask, request, render_template, send_file, render_template_string
import yt_dlp
import os
import zipfile
import shutil
import time
import subprocess

app = Flask(__name__)
DOWNLOAD_FOLDER = 'static/downloads/'
COOKIES_FILE = 'cookies.txt'

# Asegurar que la carpeta de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def check_ffmpeg():
    """ Verifica si FFmpeg está instalado """
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

if not check_ffmpeg():
    print("FFmpeg no está instalado. Por favor, instálalo y agrégalo al PATH.")
    exit(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/playlist', methods=['POST'])
def show_playlist():
    playlist_url = request.form['playlist_url'].strip()
    
    if 'music.youtube.com' not in playlist_url:
        return "Error: La URL no es válida para YouTube Music."

    try:
        ydl_opts = {
            'extract_flat': True,  # Para obtener solo los enlaces de las canciones
            'cookiefile': COOKIES_FILE,
            'force_generic_extractor': True  # Usar el extractor genérico si hay problemas
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)

        if 'entries' not in playlist_info or not playlist_info['entries']:
            return "Error: No se encontraron canciones en la playlist."

        songs = playlist_info['entries']
        playlist_title = playlist_info.get('title', 'Playlist_Sin_Nombre')

        response_message = f"<h3>{playlist_title}</h3>"
        response_message += '<form action="/download_selected" method="post">'
        response_message += f'<input type="hidden" name="playlist_title" value="{playlist_title}">'
        response_message += '<input type="button" value="Seleccionar Todas" onclick="checkAll()">'
        response_message += '<input type="button" value="Desmarcar Todas" onclick="uncheckAll()"><br>'

        for index, song in enumerate(songs, start=1):
            if 'url' in song:
                song_title = song['title']
                song_url = song['url']
                response_message += f'<input type="checkbox" name="song" value="{song_url}" checked> {index}. {song_title}<br>'

        response_message += '<br><button type="submit">Descargar Seleccionadas</button></form>'
        response_message += '''
        <script>
            function checkAll() {
                document.querySelectorAll("input[name='song']").forEach(cb => cb.checked = true);
            }
            function uncheckAll() {
                document.querySelectorAll("input[name='song']").forEach(cb => cb.checked = false);
            }
        </script>
        '''
        return render_template_string(response_message)

    except Exception as e:
        return f"Error procesando la playlist: {e}"

@app.route('/download_selected', methods=['POST'])
def download_selected():
    try:
        playlist_title = request.form['playlist_title']
        songs = request.form.getlist('song')

        if not songs:
            return "Error: No seleccionaste ninguna canción para descargar."

        playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_title)

        # Si la carpeta ya existe, limpiarla antes de descargar
        if os.path.exists(playlist_folder):
            shutil.rmtree(playlist_folder)
        os.makedirs(playlist_folder)

        for song_url in songs:
            try:
                download_and_convert(song_url, playlist_folder)
            except Exception as e:
                print(f"Error descargando {song_url}: {e}")

        if not os.listdir(playlist_folder):
            return f"Error: No se encontraron archivos en la carpeta '{playlist_folder}'."

        zip_filename = f"{playlist_title}.zip"
        zip_filepath = os.path.join(DOWNLOAD_FOLDER, zip_filename)

        # Crear el ZIP
        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for root, _, files in os.walk(playlist_folder):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), playlist_folder))

        return f"Descargas completadas. <br> <a href='/downloads/{zip_filename}'>Descargar ZIP</a>"

    except Exception as e:
        return f"Error: {e}"

def download_and_convert(video_url, playlist_folder):
    """ Descarga y convierte el video a MP3 """
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(playlist_folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'cookiefile': COOKIES_FILE,
            'noplaylist': True  # Forzar descarga de una sola canción
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        print(f"Error descargando {video_url}: {e}")

@app.route('/downloads/<filename>')
def download_file(filename):
    """ Permite descargar el ZIP y luego elimina los archivos """
    zip_filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    if not os.path.exists(zip_filepath):
        return "Error: El archivo no existe."

    response = send_file(zip_filepath, as_attachment=True)

    # Espera un poco antes de borrar los archivos para evitar errores
    time.sleep(5)

    # Elimina la carpeta de la playlist y el ZIP después de la descarga
    playlist_folder = os.path.join(DOWNLOAD_FOLDER, filename.replace('.zip', ''))
    if os.path.exists(playlist_folder):
        shutil.rmtree(playlist_folder, ignore_errors=True)

    if os.path.exists(zip_filepath):
        os.remove(zip_filepath)

    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
