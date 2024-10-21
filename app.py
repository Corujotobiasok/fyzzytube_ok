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
    playlist_url = request.form['playlist_url']

    # Verifica si es una URL válida de YouTube Music
    if 'music.youtube.com' not in playlist_url:
        return "Error: Por favor ingresa una URL válida de YouTube Music."

    try:
        # Extrae información de la playlist
        with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist'}) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            songs = playlist_info['entries']
            playlist_title = playlist_info['title']
            playlist_thumbnail = playlist_info.get('thumbnail', '')

            response_message = f"<h3>{playlist_title}</h3>"
            if playlist_thumbnail:
                response_message += f'<img src="{playlist_thumbnail}" alt="Carátula de la playlist" width="300" height="300"><br>'

            response_message += f"<h4>Playlist contiene {len(songs)} canciones:</h4>"
            response_message += '<form action="/download_selected" method="post">'
            response_message += f'<input type="hidden" name="playlist_url" value="{playlist_url}">'

            # Mostrar lista de canciones con checkboxes para seleccionar cuáles descargar
            for index, song in enumerate(songs, start=1):
                song_title = song['title']
                response_message += f'<input type="checkbox" name="song" value="{song["url"]}" checked> {index}. {song_title}<br>'

            response_message += '<button type="button" onclick="selectAll(this)">Marcar/Deseleccionar Todas</button><br><br>'
            response_message += '<button type="submit">Descargar Playlist</button>'
            response_message += '</form>'

            response_message += """
            <script>
            function selectAll(button) {
                const checkboxes = document.querySelectorAll('input[name="song"]');
                const allChecked = Array.from(checkboxes).every(checkbox => checkbox.checked);
                checkboxes.forEach(checkbox => checkbox.checked = !allChecked);
                button.textContent = allChecked ? 'Marcar Todas' : 'Deseleccionar Todas';
            }
            </script>
            """

            return render_template_string(response_message)

    except Exception as e:
        return f"Error: {e}"

@app.route('/download_selected', methods=['POST'])
def download_selected():
    selected_songs = request.form.getlist('song')
    playlist_url = request.form['playlist_url']

    if not selected_songs:
        return "Error: No seleccionaste ninguna canción para descargar."

    try:
        # Crear un directorio temporal para la playlist
        playlist_title = playlist_url.split('/')[-1]  # O alguna otra lógica para el título
        temp_folder = os.path.join(DOWNLOAD_FOLDER, playlist_title)
        os.makedirs(temp_folder, exist_ok=True)

        response_message = "<h3>Estado de la descarga:</h3>"
        downloaded_files = []

        # Descargar cada canción seleccionada
        for index, song_url in enumerate(selected_songs, start=1):
            try:
                with yt_dlp.YoutubeDL() as ydl:
                    song_info = ydl.extract_info(song_url, download=True)
                    song_title = song_info['title']
                    file_path = os.path.join(temp_folder, f"{song_title}.mp3")
                    downloaded_files.append(file_path)
                    response_message += f"<p>✔ Descargando ({index}/{len(selected_songs)}): {song_title}</p>"
            except Exception as e:
                response_message += f"<p>❌ Error descargando: {song_title}. Error: {e}</p>"

        # Crear el archivo ZIP con las canciones descargadas
        zip_filename = os.path.join(DOWNLOAD_FOLDER, f"{playlist_title}.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file_path in downloaded_files:
                zipf.write(file_path, os.path.basename(file_path))

        # Limpiar el directorio temporal
        shutil.rmtree(temp_folder)

        response_message += f'<br><a href="{url_for("download_file", filename=os.path.basename(zip_filename))}">Descargar Playlist ZIP</a>'
        return render_template_string(response_message)

    except Exception as e:
        return f"Error: {e}"

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
