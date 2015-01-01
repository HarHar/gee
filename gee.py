#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import subprocess
import threading
from Queue import Queue, Empty
from moviepy.editor import *
import os, sys
import time
key = "'" #key is '

class NonBlockingStreamReader:
    def __init__(self, stream):
        self._s = stream
        self._q = Queue()

        def _populateQueue(stream, queue):
            while True:
                line = stream.readline()
                if line:
                    queue.put(line)
                else:
                    sys.exit(0)

        self._t = threading.Thread(target = _populateQueue, args = (self._s, self._q))
        self._t.daemon = True
        self._t.start()

    def readline(self, timeout = None):
        try:
            return self._q.get(block = timeout is not None, timeout = timeout)
        except Empty:
            return None

class UnexpectedEndOfStream(Exception): pass

args = []
if '--player' in sys.argv:
	args = sys.argv
	args.remove('--player')
	for i, arg in enumerate(sys.argv):
		if arg == '--player':
			if len(sys.argv) <= i:
				print '[error] specify the player path after --player'
				exit(1)
			else:
				if os.path.exists(sys.argv[i+1]):
					playerpath = sys.argv[i+1]
				else:
					playerpath = subprocess.Popen(['/usr/bin/which', sys.argv[i+1]], stdout=-1).communicate()[0].replace('\n', '')
				args.remove(sys.argv[i+1])
else:
	args = sys.argv[1:]
	playerpath = subprocess.Popen(['/usr/bin/which', 'mplayer'], stdout=-1).communicate()[0].replace('\n', '')

if playerpath == '':
	print '[error] no player found, specify the path using --player'
	exit(1)

args.append('-slave')
args.append('-quiet')

print '[gee] using ' + repr(playerpath) + ' as player'
print ''

player = subprocess.Popen([playerpath] + args, stderr=-1, stdin=-1, stdout=-1)

def wf(stream, text):
	""" Writes and flushes a stream """
	try:
		stream.write(text + '\n')
		stream.flush
	except:
		pass

ITC = {'recording': False, 'exit': exit, 'key': key, 'playing': True, 'begin': .0, 'end': .0}

def stderr_handle(player):
	tmp = 'dummy'
	nbsr = NonBlockingStreamReader(player.stderr)
	while True:
		try:
			tmp = nbsr.readline(0.1)
		except UnexpectedEndOfStream:
			yield '*quit'
		yield tmp

def stdout_handle(player):
	tmp = 'dummy'
	nbsr = NonBlockingStreamReader(player.stdout)
	while True:
		tmp = nbsr.readline(0.1)
		yield tmp

def worker(player, itc):
	outputs = [stderr_handle(player), stdout_handle(player)]
	turn = 1
	while True:
		turn = 0 if turn != 0 else 1
		output = outputs[turn].next()
		if not output: continue
		if output == '*quit': return

		if output.find('No bind found for key \'' + itc['key'] + '\'.\n') != -1:
			if not itc['recording']:
				print '\n[gee] gif recording started'
				itc['recording'] = True

				wf(player.stdin, 'osd 1')
				wf(player.stdin, 'osd_show_text "GIF recording started" 1000 1')
				wf(player.stdin, 'get_time_pos')
			else:
				print '[gee] gif recording ended'
				itc['recording'] = False

				wf(player.stdin, 'osd 1')
				wf(player.stdin, 'osd_show_text "GIF recording ended, saving..." 1000 1')
				wf(player.stdin, 'get_time_pos')
			continue
			
		if output.replace('\n', '').startswith('ANS_TIME_POSITION'):
			if itc['recording']:
				itc['begin'] = float(output.split('=')[1].replace('\n', ''))
			else:
				itc['end'] = float(output.split('=')[1].replace('\n', ''))
				print '[gee] total gif time: ' + str(itc['end'] - itc['begin']) + 's (' + str(itc['end']) + ' - ' + str(itc['begin']) + ')'
				wf(player.stdin, 'get_file_name')
		elif output.replace('\n', '').startswith('ANS_FILENAME'):
			filename = eval(output.split('=')[1])
			saveto = str(time.time()) + '.gif'

			#here we record
			VideoFileClip(filename).subclip(itc['begin'], itc['end']).resize(0.3).to_gif(saveto)
			wf(player.stdin, 'osd 1')
			wf(player.stdin, 'osd_show_text "Saved to \'' + saveto + '\'" 2000 1')
		else:
			if not output.startswith('A: '):
				sys.stdout.write(output)
				sys.stdout.flush()

worker(player, ITC)
