from flask import Flask, request, render_template, render_template_string, send_file
import yt_dlp
import os
import shutil
import zipfile
from io import BytesIO

app = Flask(__name__)
DOWNLOAD_FOLDER = 'static/downloads/'
COOKIES_FILE = 'cookies.txt'  # Archivo de cookies

# Asegúrate de que la carpeta de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Página principal
@app.route('/')
def index():
    return render_template('index.html')

# Función para extraer las canciones de una o varias playlists
@app.route('/playlist', methods=['POST'])
def show_playlist():
    playlist_urls = request.form['playlist_url'].split(',')  # Separar por coma
    all_songs = []
    playlists_info = []

    for playlist_url in playlist_urls:
        try:
            # Verifica si es una URL válida de YouTube Music
            if 'music.youtube.com' not in playlist_url:
                return f"Error: {playlist_url} no es una URL válida de YouTube Music."

            # Extrae la información de la playlist utilizando las cookies
            ydl_opts = {
                'extract_flat': 'in_playlist',
                'cookiefile': COOKIES_FILE  # Usar el archivo de cookies
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url.strip(), download=False)
                songs = playlist_info['entries']
                playlist_title = playlist_info['title']
                playlist_thumbnail = playlist_info.get('thumbnail', '')
                playlists_info.append({
                    'title': playlist_title,
                    'thumbnail': playlist_thumbnail,
                    'songs': songs
                })
                all_songs.append(songs)

        except Exception as e:
            return f"Error al procesar {playlist_url}: {e}"

    # Renderizar una página dinámica mostrando las playlists y las canciones
    response_message = "<h3>Playlists encontradas:</h3>"
    response_message += '<form action="/download_selected" method="post">'
    for playlist in playlists_info:
        response_message += f"<h4>{playlist['title']}</h4>"
        if playlist['thumbnail']:
            response_message += f'<img src="{playlist["thumbnail"]}" alt="Carátula" width="300" height="300"><br>'

        response_message += f"<p>Playlist contiene {len(playlist['songs'])} canciones:</p>"
        response_message += '<div>'
        response_message += f'<input type="checkbox" id="select_all_{playlist["title"]}" onclick="toggleSelectAll(this, \'{playlist["title"]}\')"> Seleccionar/Desmarcar todas<br>'
        for index, song in enumerate(playlist['songs'], start=1):
            song_title = song['title']
            song_url = song['url']
            response_message += f'<input type="checkbox" name="song_url" value="{song_url}" class="{playlist["title"]}" checked> {index}. {song_title}<br>'
        response_message += '</div>'

    response_message += '<br><button type="submit">Siguiente</button>'
    response_message += '</form>'
    response_message += '''
        <script>
        function toggleSelectAll(source, playlistTitle) {
            checkboxes = document.getElementsByClassName(playlistTitle);
            for(var i=0, n=checkboxes.length; i<n; i++) {
                checkboxes[i].checked = source.checked;
            }
        }
        </script>
    '''

    return render_template_string(response_message)

# Función para descargar las canciones seleccionadas
@app.route('/download_selected', methods=['POST'])
def download_selected():
    selected_songs = request.form.getlist('song_url')
    
    if not selected_songs:
        return "Error: No seleccionaste ninguna canción para descargar."

    try:
        zip_buffer = BytesIO()  # Buffer en memoria para almacenar el archivo ZIP

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for song_url in selected_songs:
                with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'cookiefile': COOKIES_FILE}) as ydl:  # Usar el archivo de cookies
                    song_info = ydl.extract_info(song_url, download=False)
                    song_title = song_info['title']
                    playlist_title = song_info.get('playlist_title', 'Sin nombre')
                    song_filename = f'{DOWNLOAD_FOLDER}{song_title}.mp3'
                    
                    # Descarga y conversión a mp3
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': song_filename,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'cookiefile': COOKIES_FILE  # Usar el archivo de cookies
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([song_url])

                    # Guardar en la carpeta de la playlist dentro del ZIP
                    with open(song_filename, 'rb') as file_data:
                        zip_file.writestr(f'{playlist_title}/{os.path.basename(song_filename)}', file_data.read())

        zip_buffer.seek(0)  # Volver al inicio del buffer

        return send_file(zip_buffer, as_attachment=True, download_name="playlists.zip", mimetype='application/zip')

    except Exception as e:
        return f"Error descargando canciones: {e}"

if __name__ == '__main__':
    app.run(debug=True)
