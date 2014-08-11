#! /usr/bin/python

from midiutil.MidiFile import MIDIFile
import re
import simplejson as json
import sys

track_count = 0

def main():
    if len(sys.argv) is 1:
        return
    song_descriptor_path = sys.argv[1]
    with open(song_descriptor_path, 'r') as f:
        read_data = f.read()
    song_descriptor = json.loads(read_data)
    midi_file = MIDIFile(len(song_descriptor['tracks']))
    for track in song_descriptor['tracks']:
        make_midi(midi_file, track)

    with open("test.mid", 'wb') as outf:
        midi_file.writeFile(outf)

def make_midi(midi_file, track):
    global track_count
    track_id = track_count
    track_count += 1

    name = track.get('name', 'track%d'%track_id)
    midi_file.addTrackName(track_id, 0, name)

    channel = 0
    volume = 100
    offset = 0

    context = {
        'channel': 0,
        'volume': 100,
        'offset': 0,
        'midi_file': midi_file,
        'track': track,
        'track_id': track_id
    }

    process_bars(context, track['bars'])

def is_bar(bar_or_bars):
    return not bar_or_bars.has_key('sequence')

def process_bars(context, bars):
    repeat = bars.get('repeat', 1)
    for i in range(repeat):
        print bars
        for bar_or_bars in bars['sequence']:
            if is_bar(bar_or_bars):
                process_bar(context, bar_or_bars)
            else:
                process_bars(context, bar_or_bars)

def process_bar(context, bar):
    bar_length = bar.get('length', 4)
    notes = parse_rhythm(bar['rhythm'], bar_length, context['track']['type'])
    midi_file = context['midi_file']
    track_id = context['track_id']
    channel = context['channel']
    volume = context['volume']

    repeat = bar.get('repeat', 1)
    for i in range(repeat):
        for note in notes:
            midi_file.addNote(track_id, channel, note['pitch'], context['offset'] + note['time'], note['duration'], volume)
        context['offset'] += bar_length

def parse_rhythm(rhythm_string, bar_length, track_type):
    tokens = tokenize(rhythm_string)

    current_offset = 0
    interval = float(bar_length)/len(tokens)

    current_note = None
    result = []
    for token in tokens:
        if token in ('o', 'x'):
            if current_note:
                current_note['duration'] = current_offset - current_note['time']
                if track_type == 'rhythm':
                    current_note['duration'] /= float(2)
                result += [current_note]
                current_note = None
            if token is 'o':
                if track_type == 'rhythm':
                    note = 'C1'
                elif track_type == 'random-arpeggio':
                    note = get_random_note(bar)
                else:
                    note = 'C3'
                current_note = {'pitch': symbol_to_value(note), 'time': current_offset}
        current_offset += interval

    if current_note:
        current_note['duration'] = current_offset - current_note['time']
        if track_type == 'rhythm':
            current_note['duration'] /= float(2)
        result += [current_note]

    return result

def get_random_note(bar):
    base_offset, notes = parse_chord_symbol(bar['chord'])
# get one of the notes randomly
# return base_offset + randomly choiced note(offset)

def parse_chord_symbol(symbol):
    pass
# parse and return (bass_offset, array of note offset)

def symbol_to_value(symbol):
    C0 = 24
    map = {
            'C': 0,
            'D': 2,
            'E': 4,
            'F': 5,
            'G': 7,
            'A': 9,
            'B': 11
            }
    temp_signature = symbol.count('#')
    symbol = symbol.replace('#', '')
    temp_signature -= symbol.count('b')
    symbol = symbol.replace('b', '')

    result = C0 + map[symbol[0]]
    result += int(symbol[1:]) * 12
    return result + temp_signature

def tokenize(string):
    string = string.replace(' ', '')
    return re.findall('o|x|-|1?[0-9]', string)

if __name__ == "__main__":
    main()
    print symbol_to_value('C1')
    print symbol_to_value('C2')
    print symbol_to_value('D2')
    print symbol_to_value('Db2')
    print symbol_to_value('D#2')
