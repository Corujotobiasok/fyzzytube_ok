from flask import Flask, request, render_template, render_template_string, send_from_directory, url_for
import yt_dlp
import os
import shutil  # Para empaquetar en ZIP

app = Flask(__name__)
DOWNLOAD_FOLDER = 'static/downloads/'
COOKIES_FILE = 'cookies.txt'  # Archivo de cookies exportadas

# Asegúrate de que la carpeta de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/playlist', methods=['POST'])
def show_playlist():
    playlist_urls = [url.strip() for url in request.form['playlist_url'].split(',')]

    response_message = "<form action='/download_selected' method='post'>"

    for i, playlist_url in enumerate(playlist_urls):
        if 'music.youtube.com' not in playlist_url:
            response_message += f"<p>Error: '{playlist_url}' no es una URL válida de YouTube Music.</p>"
            continue

        try:
            ydl_opts = {
                'extract_flat': 'in_playlist',
                'cookiefile': COOKIES_FILE,  # Usa el archivo de cookies
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                songs = playlist_info['entries']
                playlist_title = playlist_info['title']
                playlist_thumbnail = playlist_info.get('thumbnail', '')

                response_message += f"<h3>{playlist_title}</h3>"
                if playlist_thumbnail:
                    response_message += f'<img src="{playlist_thumbnail}" alt="Carátula de la playlist" width="300" height="300"><br>'

                response_message += f"<h4>Playlist contiene {len(songs)} canciones:</h4>"
                response_message += f'<input type="hidden" name="playlist_url_{i}" value="{playlist_url}">'
                response_message += f"""
                <button type="button" onclick="toggleSelection('playlist_{i}', true)">Seleccionar Todas</button>
                <button type="button" onclick="toggleSelection('playlist_{i}', false)">Deseleccionar Todas</button><br><br>
                """

                response_message += f'<div id="playlist_{i}">'
                for index, song in enumerate(songs, start=1):
                    song_title = song['title']
                    response_message += f'<input type="checkbox" name="song_{i}" value="{song["url"]}" checked> {index}. {song_title}<br>'
                response_message += '</div><br>'

        except Exception as e:
            response_message += f"<p>Error procesando '{playlist_url}': {e}</p>"

    response_message += '<button type="submit">Descargar Todas las Playlists</button>'
    response_message += '</form>'

    response_message += """
    <script>
    function toggleSelection(playlistId, selectAll) {
        const checkboxes = document.querySelectorAll(`#${playlistId} input[type='checkbox']`);
        checkboxes.forEach(checkbox => checkbox.checked = selectAll);
    }
    </script>
    """

    return render_template_string(response_message)

@app.route('/download_selected', methods=['POST'])
def download_selected():
    playlists = {}
    for key in request.form.keys():
        if key.startswith('playlist_url_'):
            index = key.split('_')[-1]
            playlist_url = request.form[key]
            selected_songs = request.form.getlist(f'song_{index}')
            if selected_songs:
                playlists[playlist_url] = selected_songs

    if not playlists:
        return "Error: No seleccionaste ninguna canción para descargar."

    # Creamos una lista para guardar los directorios de cada playlist
    playlist_folders = []

    for playlist_url, songs in playlists.items():
        try:
            with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'cookiefile': COOKIES_FILE}) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                playlist_title = playlist_info['title']

            playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_title)
            if not os.path.exists(playlist_folder):
                os.makedirs(playlist_folder)

            playlist_folders.append(playlist_folder)

            for index, song_url in enumerate(songs, start=1):
                try:
                    download_status = download_and_convert(song_url, playlist_folder)
                except Exception as e:
                    print(f"Error descargando {song_url}: {e}")

        except Exception as e:
            print(f"Error procesando '{playlist_url}': {e}")

    # Empaquetar en ZIP
    zip_filename = 'playlists.zip'
    zip_filepath = os.path.join(DOWNLOAD_FOLDER, zip_filename)

    with shutil.ZipFile(zip_filepath, 'w') as zipf:
        for folder in playlist_folders:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder))

    # Enviar el ZIP al navegador
    return send_from_directory(DOWNLOAD_FOLDER, zip_filename, as_attachment=True)

def download_and_convert(video_url, playlist_folder):
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
            'verbose': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
