from flask import Flask, request, render_template, send_file
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
from deep_translator import GoogleTranslator  # Usamos deep-translator en lugar de googletrans
import genanki
import os

app = Flask(__name__)

# Asegurarse de que las carpetas para audio e imágenes existan
os.makedirs("static/audio", exist_ok=True)
os.makedirs("static/images", exist_ok=True)

def traducir_palabra(palabra_es):
    """Traduce la palabra de español a inglés usando deep-translator."""
    translator = GoogleTranslator(source='es', target='en')
    palabra_en = translator.translate(palabra_es)
    print(f"Traduciendo '{palabra_es}' a '{palabra_en}'")  # Depuración
    return palabra_en

def generar_audio(palabra_en):
    """Genera un archivo de audio en inglés con gTTS."""
    print(f"Generando audio para: {palabra_en}")  # Depuración
    tts = gTTS(text=palabra_en, lang='en', slow=False)
    audio_path = f"static/audio/{palabra_en}.mp3"
    tts.save(audio_path)
    return audio_path

def obtener_oracion_ejemplo(palabra_en):
    """Obtiene una oración de ejemplo del diccionario de Cambridge mediante scraping."""
    url = f"https://dictionary.cambridge.org/dictionary/english/{palabra_en}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Buscar ejemplo en la sección de definiciones
    ejemplo = soup.select_one('div.def-block div.examp')  # Selector más específico para ejemplos
    if ejemplo:
        return ejemplo.text.strip()
    return f"{palabra_en.capitalize()} is a common word in English."  # Respaldo

def guardar_imagen(imagen, palabra_en):
    """Guarda la imagen subida por el usuario, si existe."""
    if imagen and imagen.filename:
        imagen_path = f"static/images/{palabra_en}.jpg"
        imagen.save(imagen_path)
        return imagen_path
    return None

def crear_flashcard(palabra_es, imagen):
    """Crea un archivo .apkg para Anki con la palabra, audio, oración e imagen."""
    palabra_en = traducir_palabra(palabra_es)
    audio_path = generar_audio(palabra_en)
    oracion = obtener_oracion_ejemplo(palabra_en)
    imagen_path = guardar_imagen(imagen, palabra_en)

    # Definir modelo de Anki
    modelo = genanki.Model(
        1607392319,
        'Vocabulario',
        fields=[
            {'name': 'Español'},
            {'name': 'Inglés'},
            {'name': 'Audio'},
            {'name': 'Oración'},
            {'name': 'Imagen'},
        ],
        templates=[{
            'name': 'Card 1',
            'qfmt': '{{Español}}',
            'afmt': '{{Inglés}}<br>{{Audio}}<br>{{Oración}}<br>{{Imagen}}',
        }]
    )

    # Crear mazo
    mazo = genanki.Deck(2059400110, 'Vocabulario Inglés')

    # Añadir nota
    campos = [
        palabra_es,
        palabra_en,
        f"[sound:{os.path.basename(audio_path)}]",
        oracion
    ]
    if imagen_path:
        campos.append(f"<img src='{os.path.basename(imagen_path)}'>")
    else:
        campos.append("")
    
    nota = genanki.Note(model=modelo, fields=campos)
    mazo.add_note(nota)

    # Añadir archivos multimedia
    paquete = genanki.Package(mazo)
    paquete.media_files = [audio_path]
    if imagen_path:
        paquete.media_files.append(imagen_path)

    # Guardar el archivo
    output_file = f"flashcard_{palabra_en}.apkg"
    paquete.write_to_file(output_file)
    return output_file

@app.route('/', methods=['GET', 'POST'])
def index():
    """Ruta principal de la aplicación."""
    if request.method == 'POST':
        palabra_es = request.form['palabra']
        imagen = request.files.get('imagen')
        flashcard = crear_flashcard(palabra_es, imagen)
        return send_file(flashcard, as_attachment=True, download_name=f"flashcard_{palabra_es}.apkg")
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)