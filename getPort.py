import js2py
import sys
import os


dir_path = os.path.dirname(os.path.realpath(__file__))
eval_result, example = js2py.run_file(dir_path + '/static/scripts/proxyport.js')

if len(sys.argv) > 1:
	print(example.crc16(sys.argv[1]))
else:
	print("example usage python3 " + sys.argv[0] + " test-rhildred.rhlab.io")
