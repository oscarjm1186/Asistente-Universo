import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
import time
from datetime import datetime
import subprocess
import re
from io import BytesIO
import webbrowser
import locale
import pygame
import requests
import speech_recognition as sr
from gtts import gTTS

class Asistente:
    
    def __init__(self, activacion=None, key_clima=None):
        if not activacion:
            self.activacion = ["universo", "Hola universo", "Oye universo"]
        elif isinstance(activacion, str):
            self.activacion = [activacion]
        elif isinstance(activacion, (tuple, list)):
            self.activacion = list(activacion)
        else:
            raise ValueError(f'ERROR: dato no válido: {activacion}')
        self.key_clima = key_clima
        self.codificacion = locale.getpreferredencoding()
        
    def _get_microfonos(self):
        try:
            mics = sr.Microphone.list_microphone_names()
            mic_dict = {i: mic.encode(self.codificacion).decode('utf-8') for i, mic in enumerate(mics)}
            return mic_dict
        except Exception as e:
            raise Exception(f'Error al obtener micrófonos: {e}')
    
    def escuchar(self, mic=None):
        api = sr.Recognizer()
        with sr.Microphone(device_index=mic) as fuente:
            print("\33[KEscuchando...", end="\r", flush=True)
            audio = api.listen(fuente)
        
        # Transcripción vía Google    
        print("\33[KTranscribiendo...", end="\r", flush=True)
        try:
            comando = api.recognize_google(audio, language='es-ES')
            print(f"\33[KTú: {comando}")
            return comando
        except sr.UnknownValueError:
            print("No se entendió el comando")
            return ""
        except sr.RequestError as e:
            print(f"Error al transcribir: {e}")
            return ""
            
    def hablar(self, texto):
        print(f'{self.activacion[0]}: {texto}')
        pygame.mixer.init()
        tts = gTTS(texto, lang='es')
        with BytesIO() as f:
            tts.write_to_fp(f)
            f.seek(0)
            res = subprocess.run(
                'ffmpeg -i pipe:0 -filter:a atempo=1.3 -f wav pipe:1',
                shell=True,
                input=f.read(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
        audio_data = res.stdout
        with BytesIO(audio_data) as audio_file:
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.5)
                
    def _activar(self, comando):
        for act in self.activacion:
            if act.lower() in comando.lower():
                return act.lower()
        return False
    
    def _texto_en_comando(self, texto, comando):
        return re.search(r'\b' + texto + r'\b', comando, flags=re.IGNORECASE)
    
    def abrir_en_youtube(self, prompt):
        prompt2 = prompt.replace(' ', '+')
        url = f'https://www.youtube.com/results?q={prompt2}'
        req = requests.get(url)
        if req.ok:
            match = re.search(r'"videoId":"(.+?)"', req.text)
            if match:
                video_id = match.group(1)
                url_video = f'https://www.youtube.com/watch?v={video_id}'
                self.hablar(f'Okey. Abriendo {prompt} en Youtube')
                webbrowser.open(url_video)
                return url_video
        return False
    
    def clima(self, ciudad):
        if not self.key_clima:
            return "Ni idea, no metiste tu API Key vato"
        url = f'https://api.openweathermap.org/data/2.5/weather?q={ciudad}&appid={self.key_clima}&lang=es&units=metric'
        req = requests.get(url)
        if req.ok:
            d = req.json()
            temperatura = int(d["main"]["temp"])
            descripcion = d["weather"][0]["description"]
            return f'En {ciudad.strip()} la temperatura es de {temperatura} grados con {descripcion}'
        else:
            return f'No he podido obtener información de {ciudad}'
    
    def procesar_comando(self, comando):
        if self._texto_en_comando("hora", comando):
            ahora = datetime.now()
            self.hablar(f"Son las {ahora.hour}:{ahora.minute}")
        elif self._texto_en_comando("youtube ", comando):
            partes = comando.lower().split("youtube ")
            if len(partes) <= 1:
                self.hablar('Dime que quieres que busque en YouTube')
                return True
            else:
                prompt = partes[-1]
                res = self.abrir_en_youtube(prompt)
                if not res:
                    self.hablar('No encontré nada en YouTube')
        elif self._texto_en_comando("tiempo", comando):
            partes = comando.split("en ")
            if len(partes) <= 1:
                self.hablar('Que ciudad te interesa')
                return True
            else:
                ciudad = partes[-1]
                tiempo = self.clima(ciudad)
                self.hablar(tiempo)
        elif self._texto_en_comando("salir", comando):
            self.hablar("Chao baby")
            return False
        else:
            self.hablar("No te puedo ayudar")
        return True
                    
    def start(self, mic=None):
        while True:
            comando = self.escuchar(mic)
            activar = self._activar(comando)
            if activar:
                comando = re.sub(activar, "", comando, count=1).strip()
                if comando:
                    if not self.procesar_comando(comando):
                        break

if __name__ == "__main__":
    MIC = None
    asistente = Asistente(
        activacion="universo",
        key_clima="253c1f7336b0fcc1e46cfab7e45b7926",
    )
    if MIC is None:
        mics = asistente._get_microfonos()
        if len(mics) > 1:
            for k, v in mics.items():
                print(f'[{k}] {v}')
            while True:
                opcion = input(f'Selecciona un microfono: ')
                try:
                    opcion = int(opcion)
                except ValueError:
                    print('ERROR: Opción no válida')
                    continue
                if opcion not in mics:
                    print('ERROR: La opción no está en la lista')
                    continue
                else:
                    MIC = opcion
                    break
        elif not mics:
            raise Exception('ERROR: No se ha detectado ningún micrófono')
        
    asistente.start(mic=MIC)
