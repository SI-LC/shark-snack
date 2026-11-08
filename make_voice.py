#!/usr/bin/env python3
"""Records every spoken line in the game into voice.js, using the Mac's built-in voice.

Run this again after adding questions to index.html:  python3 make_voice.py
Lines already in voice.js are kept. To change the voice, delete voice.js first.
Any line without a recording falls back to the browser's own voice, if it has one.
If you change the templates in makeQuestion(), change them below too.
"""
import base64, json, os, re, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE = 'Daniel'

html = open(os.path.join(HERE, 'index.html'), encoding='utf-8').read()
lines = set()

# Fixed questions
for q, spoken in re.findall(r"^\s*\{ q: '(.+?)',(?: say: '(.+?)',)? answers: \[", html, re.M):
    lines.add(spoken or q)

# Generated questions (same ranges as makeQuestion)
for a in range(3, 13):
    for b in range(2, 9):
        lines.add(f'What is {a} plus {b}?')
for a in range(8, 21):
    for b in range(2, 9):
        lines.add(f'What is {a} take away {b}?')
for a in range(2, 10):
    for b in range(2, 10):
        lines.add(f'{a} plus what number makes {a + b}?')
for a in range(3, 11):
    lines.add(f'What is double {a}?')
for a in range(2, 11):
    lines.add(f'What is half of {a * 2}?')
for a in range(6, 13):
    for b in range(3, 6):
        lines.add(f'A shark sees {a} fish. Then {b} more fish swim up. How many fish are there now?')
        lines.add(f'There are {a} fish. Then {b} fish swim away. How many fish are left?')
for name in ['fish', 'crabs', 'turtles', 'octopuses']:
    lines.add(f'How many {name} are there? Count them carefully.')

# Challenge questions (same ranges as makeChallenge)
for a in [2, 5, 10]:
    for b in range(2, 11):
        lines.add(f'What is {a} times {b}?')
for a in range(13, 26):
    for b in range(6, 10):
        lines.add(f'What is {a} plus {b}?')
for a in range(21, 31):
    for b in range(6, 10):
        lines.add(f'What is {a} take away {b}?')
for a in range(2, 6):
    for b in range(2, 6):
        for c in range(2, 6):
            lines.add(f'What is {a} plus {b} plus {c}?')
for boxes in range(2, 6):
    for each in [2, 5, 10]:
        lines.add(f'There are {boxes} nets with {each} fish in each net. How many fish are there altogether?')

# Explanations for fixed questions
lines.update(re.findall(r"why: '(.+?)' \},$", html, re.M))

# Explanations for generated questions
for a, b in [(a, b) for a in range(3, 13) for b in range(2, 9)] + [(a, b) for a in range(13, 26) for b in range(6, 10)]:
    lines.add(f'{a} plus {b} is {a + b}. Start at {a} and count on {b}.')
for a, b in [(a, b) for a in range(8, 21) for b in range(2, 9)] + [(a, b) for a in range(21, 31) for b in range(6, 10)]:
    lines.add(f'{a} take away {b} is {a - b}. Start at {a} and count back {b}.')
for a in range(2, 10):
    for b in range(2, 10):
        lines.add(f'The answer is {b}, because {a} plus {b} makes {a + b}.')
for a in range(3, 11):
    lines.add(f'Double {a} means {a} plus {a}, which is {a * 2}.')
for a in range(2, 11):
    lines.add(f'Half of {a * 2} is {a}, because {a} plus {a} makes {a * 2}.')
for a in range(6, 13):
    for b in range(3, 6):
        lines.add(f'{a} plus {b} is {a + b}, so there are {a + b} fish.')
        lines.add(f'{a} take away {b} is {a - b}, so {a - b} fish are left.')
for n in range(7, 19):
    lines.add(f'There are {n}. Count in fives along the rows, then add the rest.')
for a in [2, 5, 10]:
    for b in range(2, 11):
        lines.add(f'{a} times {b} is {a * b}. That is {b} lots of {a}.')
for a in range(2, 6):
    for b in range(2, 6):
        for c in range(2, 6):
            lines.add(f'{a} plus {b} is {a + b}, and {c} more makes {a + b + c}.')
for boxes in range(2, 6):
    for each in [2, 5, 10]:
        lines.add(f'{boxes} nets of {each} is {boxes * each}. Count in {each}s.')

# Dictation (same wording as dictation() in index.html)
for word, sentence in re.findall(r"^\s*\['([a-z]+)', '(.+?)'\],$", html, re.M):
    Word = word[0].upper() + word[1:]
    lines.add(f'{Word}. {sentence} {Word}.')
    lines.add(f"{Word} is spelled {', '.join(word)}.")
for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    lines.add(letter)

# Praise
lines.add('Nearly! Try again.')
lines.add('A new baby shark has joined you!')
lines.add('Your baby sharks grew bigger!')
lines.add('Bubble boost!')
lines.add('You unlocked the bubble boost! Catch the big bubbles to zoom!')
lines.add('You unlocked sharp teeth! Now you can bite jellyfish and tough fish!')
lines.add('You did it! Your baby shark army is all grown up!')
lines.add('Baby to the rescue! Your biggest baby takes over!')
lines.add('Well done! You won rainbow power!')
for prize in re.findall(r"\{ name: '(.+?)',", html):
    lines.add(f'Well done! You won {prize} and rainbow power!')

def letters(text):
    # Make sure single letters are said as letter names: "a" as "ay", not "uh"
    letter = lambda c: f'[[char LTRL]]{c}[[char NORM]]'
    if re.fullmatch(r'[A-Z]', text):
        return letter(text)
    return re.sub(r'is spelled ((?:[a-z], )*[a-z])\.$',
                  lambda m: 'is spelled ' + ', '.join(letter(c) for c in m[1].split(', ')) + '.', text)

def record(job):
    index, line, folder = job
    aiff = os.path.join(folder, f'{index}.aiff')
    m4a = os.path.join(folder, f'{index}.m4a')
    subprocess.run(['say', '-v', VOICE, '-o', aiff, letters(line)], check=True)
    subprocess.run(['afconvert', aiff, m4a, '-f', 'm4af', '-d', 'aac@22050', '-b', '32000', '-c', '1'], check=True)
    with open(m4a, 'rb') as f:
        return line, base64.b64encode(f.read()).decode()

voice_file = os.path.join(HERE, 'voice.js')
kept = {}
if os.path.exists(voice_file):
    saved = open(voice_file, encoding='utf-8').read()
    saved = json.loads(saved[saved.index('{'):saved.rindex('}') + 1])
    kept = {line: clip for line, clip in saved.items() if line in lines}

with tempfile.TemporaryDirectory() as folder:
    jobs = [(i, line, folder) for i, line in enumerate(sorted(lines - kept.keys()))]
    with ThreadPoolExecutor(6) as pool:
        clips = {**kept, **dict(pool.map(record, jobs))}

with open(voice_file, 'w', encoding='utf-8') as f:
    f.write('// Made by make_voice.py. Spoken lines as base64 audio.\nwindow.VOICE = ')
    json.dump(clips, f, ensure_ascii=False, indent=0)
    f.write(';\n')
print(len(clips), 'lines in total,', len(jobs), 'newly recorded')
