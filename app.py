from flask import Flask, request, render_template, render_template_string, send_from_directory
import yt_dlp
import os

app = Flask(__name__)
DOWNLOAD_FOLDER = 'static/downloads/'
COOKIES_FILE = 'cookies.txt'

# Asegúrate de que la carpeta de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/playlist', methods=['POST'])
def show_playlist():
    playlist_urls = request.form['playlist_url'].split(',')

    response_message = '<h3>Selecciona las canciones para descargar:</h3>'
    for playlist_url in playlist_urls:
        playlist_url = playlist_url.strip()

        # Verificar si es una URL válida de YouTube Music
        if 'music.youtube.com' not in playlist_url:
            response_message += f"Error: La URL '{playlist_url}' no es válida para YouTube Music.<br>"
            continue

        try:
            # Extrae la información de la playlist o canción
            with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'cookiefile': COOKIES_FILE}) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                songs = playlist_info.get('entries', [playlist_info])  # Maneja una sola canción o playlist
                playlist_title = playlist_info.get('title', 'Sin Título')

                response_message += f"<h4>{playlist_title}</h4>"
                response_message += f'<input type="hidden" name="playlist_url" value="{playlist_url}">'
                response_message += '<div>'

                # Mostrar lista de canciones con checkboxes
                for index, song in enumerate(songs, start=1):
                    song_title = song['title']
                    response_message += f'<input type="checkbox" name="song_{playlist_url}" value="{song["url"]}" checked> {index}. {song_title}<br>'

                response_message += '</div><br>'

        except Exception as e:
            response_message += f"Error procesando '{playlist_url}': {e}<br>"

    response_message += '<br><button type="submit">Descargar Seleccionadas</button>'
    return render_template_string(f'''
    <form method="POST" action="/download_selected">
        {response_message}
    </form>
    ''')

@app.route('/download_selected', methods=['POST'])
def download_selected():
    try:
        playlists = {}

        # Recoger todas las canciones seleccionadas
        for key in request.form.keys():
            if key.startswith('song_'):
                playlist_url = key.split('_', 1)[1]
                selected_songs = request.form.getlist(key)
                if selected_songs:
                    playlists[playlist_url] = selected_songs

        if not playlists:
            return "Error: No seleccionaste ninguna canción para descargar."

        # Descargar las canciones seleccionadas
        for playlist_url, selected_songs in playlists.items():
            with yt_dlp.YoutubeDL({'cookiefile': COOKIES_FILE}) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                playlist_title = playlist_info.get('title', 'Sin Título')

                # Crear carpeta para la playlist
                playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_title)
                if not os.path.exists(playlist_folder):
                    os.makedirs(playlist_folder)

                # Descargar cada canción seleccionada
                for song_url in selected_songs:
                    download_song(song_url, playlist_folder)

        return "Descargas completadas"

    except Exception as e:
        return f"Error: {e}"

def download_song(video_url, playlist_folder):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(playlist_folder, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'cookiefile': COOKIES_FILE,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
