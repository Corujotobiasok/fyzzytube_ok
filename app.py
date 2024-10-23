from flask import Flask, request, render_template, render_template_string, send_from_directory, url_for
import yt_dlp
import os
import shutil
import zipfile

app = Flask(__name__)
DOWNLOAD_FOLDER = 'static/downloads/'
COOKIES_FILE = 'cookies.txt'

# Asegurarse de que la carpeta de descargas existe
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

# Maneja la extracción de información de la playlist/canción y muestra las opciones
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
            # Usamos cookies para evitar restricciones de acceso
            ydl_opts = {'extract_flat': 'in_playlist', 'cookiefile': COOKIES_FILE}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                songs = playlist_info['entries']
                playlist_title = playlist_info['title']
                playlist_thumbnail = playlist_info.get('thumbnail', '')

                # Renderiza la lista de canciones
                response_message += f"<h3>{playlist_title}</h3>"
                if playlist_thumbnail:
                    response_message += f'<img src="{playlist_thumbnail}" alt="Carátula de la playlist" width="300" height="300"><br>'

                response_message += f"<h4>Playlist contiene {len(songs)} canciones:</h4>"
                response_message += '<form action="/download_selected" method="post">'
                response_message += f'<input type="hidden" name="playlist_url" value="{playlist_url}">'
                response_message += f'<input type="hidden" name="playlist_title" value="{playlist_title}">'
                response_message += '<input type="button" value="Seleccionar Todas" onclick="checkAll(this)">'
                response_message += '<input type="button" value="Desmarcar Todas" onclick="uncheckAll(this)"><br>'

                # Lista de canciones con checkboxes
                for index, song in enumerate(songs, start=1):
                    song_title = song['title']
                    response_message += f'<input type="checkbox" name="song_{playlist_title}" value="{song["url"]}" checked> {index}. {song_title}<br>'

                response_message += '<br><button type="submit">Descargar Seleccionadas</button>'
                response_message += '</form>'

                # Funciones para seleccionar/deseleccionar todas las canciones
                response_message += '''
                <script>
                function checkAll(source) {
                    checkboxes = document.getElementsByName("song_''' + playlist_title + '''");
                    for (var i = 0, n = checkboxes.length; i < n; i++) {
                        checkboxes[i].checked = true;
                    }
                }
                function uncheckAll(source) {
                    checkboxes = document.getElementsByName("song_''' + playlist_title + '''");
                    for (var i = 0, n = checkboxes.length; i < n; i++) {
                        checkboxes[i].checked = false;
                    }
                }
                </script>
                '''

        except Exception as e:
            response_message += f"Error procesando '{playlist_url}': {e}<br>"

    return render_template_string(response_message)

# Descargar las canciones seleccionadas y crear ZIP
@app.route('/download_selected', methods=['POST'])
def download_selected():
    try:
        playlists = {}
        for key in request.form.keys():
            if key.startswith('song_'):
                playlist_title = key.split('_')[1]  # Obtiene el título de la playlist
                song_urls = request.form.getlist(key)
                if song_urls:
                    playlists[playlist_title] = song_urls

        if not playlists:
            return "Error: No seleccionaste ninguna canción para descargar."

        # Creamos una lista para guardar las rutas de cada playlist descargada
        playlist_folders = []

        for playlist_title, song_urls in playlists.items():
            # Crea una carpeta por cada playlist
            playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_title)
            if not os.path.exists(playlist_folder):
                os.makedirs(playlist_folder)
            playlist_folders.append(playlist_folder)

            # Descargar cada canción seleccionada
            for song_url in song_urls:
                download_and_convert(song_url, playlist_folder)

        # Empaquetar en ZIP
        zip_filename = 'playlists.zip'
        zip_filepath = os.path.join(DOWNLOAD_FOLDER, zip_filename)

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for folder in playlist_folders:
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder))

        # Enviar el ZIP al navegador
        return send_from_directory(DOWNLOAD_FOLDER, zip_filename, as_attachment=True)
    
    except Exception as e:
        return f"Error: {e}"

# Función para descargar y convertir las canciones a MP3
def download_and_convert(video_url, playlist_folder):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',  # Solo descarga el mejor audio
            'outtmpl': os.path.join(playlist_folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',  # Calidad de audio 192kbps
            }],
            'cookiefile': COOKIES_FILE,
            'verbose': True
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
