from flask import Flask, request, render_template, send_from_directory, render_template_string
import yt_dlp
import os
import zipfile
import subprocess

app = Flask(__name__)
DOWNLOAD_FOLDER = 'static/downloads/'
COOKIES_FILE = 'cookies.txt'

# Asegúrate de que la carpeta de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

if not check_ffmpeg():
    print("FFmpeg no está instalado. Por favor, instálalo y asegúrate de que esté en tu PATH.")
    exit(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/playlist', methods=['POST'])
def show_playlist():
    playlist_urls = request.form['playlist_url'].split(',')
    response_message = ''

    for playlist_url in playlist_urls:
        playlist_url = playlist_url.strip()
        
        if 'music.youtube.com' not in playlist_url:
            response_message += f"Error: La URL '{playlist_url}' no es válida para YouTube Music.<br>"
            continue

        try:
            # Extrae información de la playlist
            with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'cookiefile': COOKIES_FILE}) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                songs = playlist_info['entries']
                playlist_title = playlist_info['title']
                
                response_message += f"<h3>{playlist_title}</h3>"
                response_message += '<form action="/download_selected" method="post">'
                response_message += f'<input type="hidden" name="playlist_title" value="{playlist_title}">'
                response_message += '<input type="button" value="Seleccionar Todas" onclick="checkAll(this)">'
                response_message += '<input type="button" value="Desmarcar Todas" onclick="uncheckAll(this)"><br>'

                for index, song in enumerate(songs, start=1):
                    song_title = song['title']
                    response_message += f'<input type="checkbox" name="song" value="{song["url"]}" checked> {index}. {song_title}<br>'

                response_message += '<br><button type="submit">Descargar Seleccionadas</button>'
                response_message += '</form>'
                response_message += '''
                <script>
                function checkAll(source) {
                    checkboxes = document.getElementsByName("song");
                    for (var i = 0, n = checkboxes.length; i < n; i++) {
                        checkboxes[i].checked = true;
                    }
                }
                function uncheckAll(source) {
                    checkboxes = document.getElementsByName("song");
                    for (var i = 0, n = checkboxes.length; i < n; i++) {
                        checkboxes[i].checked = false;
                    }
                }
                </script>
                '''

        except Exception as e:
            response_message += f"Error procesando '{playlist_url}': {e}<br>"

    return render_template_string(response_message)

@app.route('/download_selected', methods=['POST'])
def download_selected():
    try:
        playlist_title = request.form['playlist_title']
        songs = request.form.getlist('song')

        if not songs:
            return "Error: No seleccionaste ninguna canción para descargar."

        playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_title)
        if not os.path.exists(playlist_folder):
            os.makedirs(playlist_folder)

        for song_url in songs:
            try:
                download_and_convert(song_url, playlist_folder)
            except Exception as e:
                print(f"Error descargando {song_url}: {e}")

        # Verifica si se descargaron archivos antes de crear el ZIP
        if not os.listdir(playlist_folder):
            return f"Error: No se encontraron archivos en la carpeta '{playlist_folder}'."

        # Empaquetar en ZIP
        zip_filename = f"{playlist_title}.zip"
        zip_filepath = os.path.join(DOWNLOAD_FOLDER, zip_filename)

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for root, dirs, files in os.walk(playlist_folder):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), playlist_folder))

        return f"Descargas completadas para la playlist: {playlist_title}. <br> <a href='/downloads/{zip_filename}'>Descargar ZIP</a>"
    
    except Exception as e:
        return f"Error: {e}"

def download_and_convert(video_url, playlist_folder):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',  # Descargar solo el mejor audio
            'outtmpl': os.path.join(playlist_folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'cookiefile': COOKIES_FILE,
            'verbose': True  # Activa la salida detallada
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

    except Exception as e:
        print(f"Error descargando {video_url}: {e}")

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
