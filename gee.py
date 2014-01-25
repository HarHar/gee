#!/usr/bin/env python
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
from moviepy.editor import *
import os, sys
import time
key = "'" #key is '

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

print '[gee] using ' + repr(playerpath) + ' as player'
print ''

player = subprocess.Popen([playerpath] + args, stderr=-1, stdin=-1, stdout=-1)

def wf(stream, text):
	""" Writes and flushes a stream """
	stream.write(text + '\n')
	stream.flush

ITC = {'recording': False, 'exit': exit, 'key': key, 'playing': True, 'begin': .0, 'end': .0}

def stderr_handle(player, itc):
	while True:
		tmp = player.stderr.readline()
		if tmp == 'No bind found for key \'' + itc['key'] + '\'.\n':
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
				wf(player.stdin, 'osd_show_text "GIF recording ended" 1000 1')
				wf(player.stdin, 'get_time_pos')
		else:
			if tmp.replace('\n', '') != '':
				sys.stderr.write(tmp)
				sys.stderr.flush()

		if tmp == '':
			itc['playing'] = False
			break

def stdout_handle(player, itc):
	while True:
		tmp = player.stdout.readline()
		if tmp.startswith('ANS_TIME_POSITION'):
			if itc['recording']:
				itc['begin'] = float(tmp.split('=')[1])
			else:
				itc['end'] = float(tmp.split('=')[1])
				print '[gee] total gif time: ' + str(itc['end'] - itc['begin']) + 's'
				wf(player.stdin, 'get_file_name')
		elif tmp.startswith('ANS_FILENAME'):
			filename = eval(tmp.split('=')[1])

			#here we record
			VideoFileClip(filename).subclip(itc['begin'], itc['end']).resize(0.3).to_gif(filename + '_[' + str(itc['begin']) + ' - ' + str(itc['end']) + '].gif')
			wf(player.stdin, 'osd 1')
			wf(player.stdin, 'osd_show_text "Saved to \''+ filename + '_[' + str(itc['begin']) + ' - ' + str(itc['end']) + '].gif' +'\'" 1000 1')
		else:
			if not tmp.startswith('A: '):
				sys.stdout.write(tmp)
				sys.stdout.flush()

		if tmp == '':
			break #stderr handler is the one who tells main thread to quit

threading.Thread(target=stderr_handle, args=(player, ITC,)).start()
threading.Thread(target=stdout_handle, args=(player, ITC,)).start()

while ITC['playing']:
	time.sleep(1)
exit()