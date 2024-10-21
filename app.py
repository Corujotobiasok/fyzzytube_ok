from flask import Flask, request, render_template, render_template_string, send_from_directory, url_for
import yt_dlp
import os
import zipfile
import shutil

app = Flask(__name__)
DOWNLOAD_FOLDER = 'static/downloads/'

# Asegúrate de que la carpeta de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/playlist', methods=['POST'])
def show_playlist():
    playlist_urls = request.form['playlist_url'].split(',')

    response_message = "<h3>Selecciona las canciones para descargar:</h3>"
    for playlist_url in playlist_urls:
        playlist_url = playlist_url.strip()
        if 'music.youtube.com' not in playlist_url:
            return "Error: Por favor ingresa URLs válidas de YouTube Music."

        try:
            # Extrae información de la playlist
            with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist'}) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                songs = playlist_info['entries']
                playlist_title = playlist_info['title']

                response_message += f"<h4>{playlist_title}</h4>"
                response_message += f'<input type="hidden" name="playlist_url" value="{playlist_url}">'
                response_message += '<div>'

                # Mostrar lista de canciones con checkboxes para seleccionar cuáles descargar
                for index, song in enumerate(songs, start=1):
                    song_title = song['title']
                    response_message += f'<input type="checkbox" name="song_{playlist_url}" value="{song["url"]}" checked> {index}. {song_title}<br>'

                response_message += '<button type="button" onclick="toggleCheckboxes(this)">Seleccionar/Deseleccionar todas</button>'
                response_message += '</div><br>'

        except Exception as e:
            return f"Error: {e}"

    response_message += '<br><button type="submit">Descargar Seleccionadas</button>'
    response_message += '</form>'

    return render_template_string(response_message)

@app.route('/download_selected', methods=['POST'])
def download_selected():
    try:
        playlists = {}
        # Captura las canciones seleccionadas por cada playlist
        for key in request.form.keys():
            if key.startswith('song_'):
                playlist_url = key.split('_', 1)[1]  # Extrae la URL de la clave
                selected_songs = request.form.getlist(key)
                if selected_songs:
                    playlists[playlist_url] = selected_songs

        if not playlists:
            return "Error: No seleccionaste ninguna canción para descargar."

        response_message = "<h3>Estado de la descarga:</h3>"
        for playlist_url, selected_songs in playlists.items():
            playlist_title = playlist_url.split('/')[-1]  # Usa la última parte de la URL como título

            # Crea una carpeta para la playlist
            playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_title)
            if not os.path.exists(playlist_folder):
                os.makedirs(playlist_folder)

            # Descargar cada canción seleccionada
            for index, song_url in enumerate(selected_songs, start=1):
                song_title = ""  # Inicializa song_title
                try:
                    with yt_dlp.YoutubeDL() as ydl:
                        song_info = ydl.extract_info(song_url, download=False)
                        song_title = song_info['title']
                        response_message += f"<p>Descargando ({index}/{len(selected_songs)}): {song_title}</p>"

                        download_and_convert(song_url, playlist_folder)

                        response_message += f"<p>✔ {song_title} descargado correctamente.</p>"
                except Exception as e:
                    if song_title:  # Solo accede a song_title si ha sido definido
                        response_message += f"<p>❌ Error descargando: {song_title}. Error: {e}</p>"
                    else:
                        response_message += f"<p>❌ Error al procesar la canción. Error: {e}</p>"

        # Comprimir todas las carpetas en un archivo ZIP
        zip_file_path = os.path.join(DOWNLOAD_FOLDER, 'playlists.zip')
        with zipfile.ZipFile(zip_file_path, 'w') as zipf:
            for foldername in os.listdir(DOWNLOAD_FOLDER):
                folder_path = os.path.join(DOWNLOAD_FOLDER, foldername)
                if os.path.isdir(folder_path):
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            zipf.write(os.path.join(root, file),
                                       os.path.relpath(os.path.join(root, file),
                                                       os.path.join(folder_path, '..')))

        response_message += f"<p><a href='{url_for('download_file', filename='playlists.zip')}'>Descargar todas las playlists en un ZIP</a></p>"
        return render_template_string(response_message)

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
                'preferredquality': '192',  # Calidad de audio 192kbps
            }],
            'verbose': True  # Para depurar en caso de errores
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
