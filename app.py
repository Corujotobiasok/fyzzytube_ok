from flask import Flask, request, render_template, send_file, render_template_string
import yt_dlp
import os
import zipfile
import shutil
import time
import subprocess

app = Flask(__name__)
TEMP_FOLDER = '/tmp'
COOKIES_FILE = 'cookies.txt'

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
            'extract_flat': True,
            'cookiefile': COOKIES_FILE,
            'force_generic_extractor': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)

        if 'entries' not in playlist_info or not playlist_info['entries']:
            return "Error: No se encontraron canciones en la playlist."

        songs = playlist_info['entries']
        playlist_title = playlist_info.get('title', 'Playlist_Sin_Nombre').replace(' ', '_')

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
        playlist_title = request.form['playlist_title'].replace(' ', '_')
        songs = request.form.getlist('song')

        if not songs:
            return "Error: No seleccionaste ninguna canción para descargar."

        # Crear carpeta temporal única
        timestamp = str(int(time.time()))
        playlist_folder = os.path.join(TEMP_FOLDER, f"{playlist_title}_{timestamp}")
        os.makedirs(playlist_folder, exist_ok=True)

        for song_url in songs:
            try:
                download_and_convert(song_url, playlist_folder)
            except Exception as e:
                print(f"Error descargando {song_url}: {e}")

        if not os.listdir(playlist_folder):
            return f"Error: No se descargaron canciones."

        zip_filename = f"{playlist_title}_{timestamp}.zip"
        zip_filepath = os.path.join(TEMP_FOLDER, zip_filename)

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for root, _, files in os.walk(playlist_folder):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), playlist_folder))

        return f"Descarga lista: <br><a href='/downloads/{zip_filename}?folder={os.path.basename(playlist_folder)}'>Descargar ZIP</a>"

    except Exception as e:
        return f"Error: {e}"

def download_and_convert(video_url, playlist_folder):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(playlist_folder, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'cookiefile': COOKIES_FILE,
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

@app.route('/downloads/<filename>')
def download_file(filename):
    """ Envía el archivo ZIP y elimina el contenido luego de un tiempo """
    folder = request.args.get('folder', '')
    zip_path = os.path.join(TEMP_FOLDER, filename)
    playlist_path = os.path.join(TEMP_FOLDER, folder)

    if not os.path.exists(zip_path):
        return "Error: El archivo no existe."

    response = send_file(zip_path, as_attachment=True)

    # Eliminamos después de 5 segundos en segundo plano
    def eliminar_temporales():
        time.sleep(5)
        if os.path.exists(zip_path): os.remove(zip_path)
        if os.path.exists(playlist_path): shutil.rmtree(playlist_path, ignore_errors=True)

    import threading
    threading.Thread(target=eliminar_temporales).start()

    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
