#! /usr/bin/python

import math
from midiutil.MidiFile import MIDIFile
import random
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

    print 'make_midi is done'

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

    track['bars']['parent'] = track
    process_bars(context, track['bars'])

def is_bar(bar_or_bars):
    return not bar_or_bars.has_key('sequence')

def process_bars(context, bars):
    repeat = get_property(bars, 'repeat')
    for i in range(repeat):
        print bars
        for bar_or_bars, previous in zip(bars['sequence'], [None]+bars['sequence']):
            if previous:
                bar_or_bars['parent'] = previous
            else:
                bar_or_bars['parent'] = bars
            if is_bar(bar_or_bars):
                process_bar(context, bar_or_bars)
            else:
                process_bars(context, bar_or_bars)

# FIXME: when bars is parent, it may not find its child but search directly its parent.

def process_bar(context, bar):
    raw_rhythm = get_property(bar, 'rhythm')
    style = get_property(bar, 'style')
    if style:
        with open(style['path'], 'r') as f:
            read_data = f.read()
        style_element = json.loads(read_data)
        style_element[style['name']]['parent'] = bar['parent']
        bar['parent'] = style_element[style['name']]

    bar_length = get_property(bar, 'length')
    raw_rhythm = get_property(bar, 'rhythm')
    rhythm = parse_rhythm(raw_rhythm, bar_length, context['track'].get('type', ''))
    notes = make_notes(context['track'], bar, rhythm)

    midi_file = context['midi_file']
    track_id = context['track_id']
    channel = context['channel']
    volume = context['volume']

    repeat = get_property(bar, 'repeat')
    for i in range(repeat):
        for note in notes:
            print 'repeat',i,'(', notes.index(note),'/', len(notes),')', note
            midi_file.addNote(track_id, channel, note['pitch'], context['offset'] + note['time'], note['duration'], volume)
        context['offset'] += bar_length

bar_default_value = {
  'length': 4,
  'repeat': 1,
  'base_octave': 2
}

def get_property(element, property):
    if property in element:
        return element[property]
    else:
        current = element
        while 'parent' in current:
            if property in current['parent']:
                return current['parent'][property]
            current = current['parent']
        if property in bar_default_value:
            return bar_default_value[property]

def make_notes(track, bar, rhythm):
    track_type = get_property(bar, 'type')
    base_octave = get_property(track, 'base_octave')
    if track_type == 'rhythm':
        for note in rhythm:
            note['note'] = 'C1'
            note['pitch'] = symbol_to_value(note['note'])
    elif track_type == 'random-arpeggio':
        print 'chord symbol: ', bar['chord']
        chord_tones = get_chord_tones(bar['chord'])
        print 'chord_tones:', chord_tones
        length = len(chord_tones)
        for note in rhythm:
            note['note'] = chord_tones[int(math.floor(length * random.random()))] + str(base_octave)
            note['pitch'] = symbol_to_value(note['note'])
            print 'generate..', note
    elif track_type == 'ascending-arpeggio':
        chord_tones = get_chord_tones(bar['chord'])
        length = len(chord_tones)
        for note in rhythm:
            note['note'] = chord_tones[rhythm.index(note)%length] + str(base_octave)
            note['pitch'] = symbol_to_value(note['note'])
    elif track_type == 'custom':
        chord = get_property(bar, 'chord')
        root, _, _ = parse_chord_symbol(chord)
        for note in rhythm:
            offset = int(note['interval_hint'])/7
            note['note'] = get_note_with_interval(root, note['interval_hint']) + str(base_octave+offset)
            note['pitch'] = symbol_to_value(note['note'])
    return rhythm

def parse_rhythm(rhythm_string, bar_length, track_type):
    tokens = tokenize(rhythm_string)

    current_offset = 0
    interval = float(bar_length)/len(tokens)

    current_note = None
    result = []
    for token in tokens:
        is_numeric = len(re.findall('[1-9]', token)) != 0
        if token in ('o', 'x') or is_numeric:
            if current_note:
                current_note['duration'] = current_offset - current_note['time']
                if track_type == 'rhythm':
                    current_note['duration'] /= float(2)
                result += [current_note]
                current_note = None
            if token is 'o' or is_numeric:
                current_note = {'time': current_offset}
                if is_numeric:
                    current_note['interval_hint'] = token
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

def parse_chord_symbol(chord_symbol):
    m = re.match('^(?P<root>[A-G](b|#)?)(?P<symbol>(7|maj7|m7|m)?)(?P<tension>((b|#)?(5|9|11|13))?)', chord_symbol)
    return m.group('root'), m.group('symbol'), m.group('tension')

def get_chord_tones(chord_symbol):
    root, symbol, tension = parse_chord_symbol(chord_symbol)

    result = [root]

    symbol = symbol or ''
    symbol_without_7 = symbol.replace('7', '')
    if symbol_without_7 == 'maj' or symbol_without_7 == '':
        result += [get_note_with_interval(root, '3')]
    elif symbol_without_7 == 'm':
        result += [get_note_with_interval(root, 'b3')]

    if tension == 'b5':
        result += [get_note_with_interval(root, 'b5')]
    else:
        result += [get_note_with_interval(root, '5')]

    if symbol.find('7') >= 0:
        if symbol_without_7 == 'maj':
            result += [get_note_with_interval(root, '7')]
        elif symbol_without_7 == 'm' or symbol_without_7 == '':
            result += [get_note_with_interval(root, 'b7')]

    if tension:
        result += [get_note_with_interval(root, tension)]

    return result

def get_note_with_interval(note, interval):
    value = symbol_to_value(note + '0')
    interval_map = {
            '1': 0,
            '2': 2,
            '3': 4,
            '4': 5,
            '5': 7,
            '6': 9,
            '0': 11, #7th
            }

    temp_signature = interval.count('#')
    interval = interval.replace('#', '')
    temp_signature -= interval.count('b')
    interval = interval.replace('b', '')

    interval = str(int(interval)%7)

    value_to_add = interval_map[interval] + temp_signature
    return re.sub('\d+', '', value_to_symbol(value + value_to_add))

def value_to_symbol(value):
    mapper = {
            0: 'C',
            2: 'D',
            4: 'E',
            5: 'F',
            7: 'G',
            9: 'A',
            11: 'B'
            }
    offset = int(value)%12
    if offset in mapper:
        note = mapper[offset]
    else:
        note = mapper[offset+1] + 'b'

    base = str(int(value)/12 - 2)
    return note + base


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
    return re.findall('o|x|-|[1-9]', string)

if __name__ == "__main__":
    main()
    print symbol_to_value('C1')
    print symbol_to_value('C2')
    print symbol_to_value('D2')
    print symbol_to_value('Db2')
    print symbol_to_value('D#2')
