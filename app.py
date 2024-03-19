from flask import Flask, request, send_file, render_template, after_this_request
import mido
from mido import MidiFile, MidiTrack
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit
app.config['TEMPLATES_AUTO_RELOAD'] = True

def adjust_tempo(midi, tempo_multiplier):
    for i, track in enumerate(midi.tracks):
        for j, msg in enumerate(track):
            if msg.type == 'set_tempo':
                # Adjust the tempo based on the multiplier
                new_tempo = int(msg.tempo / tempo_multiplier)
                midi.tracks[i][j] = mido.MetaMessage('set_tempo', tempo=new_tempo)
    return midi

def transpose_midi(midi, semitones):
    for track in midi.tracks:
        for msg in track:
            if msg.type in ['note_on', 'note_off']:
                msg.note = max(0, min(127, msg.note + semitones))
    return midi

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']

        radio_up_down = request.form['radio_up_down']
        semitones = int(request.form['semitones'])

        if radio_up_down == 'down':
            semitones = -semitones

        tempo_multiplier = float(request.form['tempo_multiplier'])
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            original_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(original_filepath)
            midi = MidiFile(original_filepath)
            midi = transpose_midi(midi, semitones)  # Assuming this function exists
            midi = adjust_tempo(midi, tempo_multiplier)
            modified_filename = f"processed_{filename}"
            transposed_path = os.path.join(app.config['UPLOAD_FOLDER'], modified_filename)
            midi.save(transposed_path)

            # Schedule both the original and processed files for deletion after the request has been sent
            @after_this_request
            def remove_files(response):
                try:
                    os.remove(original_filepath)
                    os.remove(transposed_path)
                except Exception as error:
                    app.logger.error("Error removing or closing downloaded file handle", error)
                return response

            return send_file(transposed_path, as_attachment=True, download_name=modified_filename)
    return render_template('upload.html')


if __name__ == '__main__':
    # Create the uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
