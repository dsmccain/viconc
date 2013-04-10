#!/usr/bin/python2
import os,sys

# TODO: Color difference with spawns?

# DEBUG = True
DEBUG = False

def debug(info):
	if DEBUG:
		print info

def file_to_node_list(f):
	''' Debug Format:
			------------
			Explore \d+
			------------
			((
				[

				Replay (\d+) is required...
				Done replaying...

				]
				Plan: ...
				Happened before: ...
				Selected: ...
				Pick next: Enabled: [...] Sleeping: [...]
				Picked: [...]
			))
			|
			((
				Backtrack set explored
				[NORMAL!|DEADLOCK!|SLEEP SET BLOCK]
				Stack frame dropped
			))
			|
			((
				ERROR!
				...
			))
	'''
	regex = "(?:------------)\n" +\
			"(?:Explore (\d+))\n" +\
			"(?:------------)\n" +\
			"(?:" +\
				"(?:" +\
					"\nReplay \((\d+)\) is required\.\.\.\n" +\
					"Done replaying\.\.\.\n\n" +\
				")?" +\
				"(Plan: \{.*\})\n" +\
				"(Happened before: \[(?:\s*\{\"[\d.]+\",\d+\},?)*\])\n" +\
				"(Selected: \{\"[\d.]+\",(?:\n\s+.+|.+)+\})\n" +\
				"(Pick next: Enabled: \[(?:\s*\"[\d.]+\",?)*\]" +\
					" Sleeping: \[(?:\s*\"[\d.]+\",?)*\])\n" +\
				"(Picked: \[(?:\"[\d.]+\")?\])\n" +\
			"|" +\
				"Backtrack set explored\n" +\
				"(?:(?:(NORMAL|DEADLOCK)!|SLEEP SET BLOCK)\n)?" +\
				"Stack frame dropped\n" +\
			"|" +\
				"ERROR!\n" +\
				"(\{\"[\d.]+\",\n\s*(?:\n\s+.+|.+)+\}\n)" +\
			")"

	# print ">>>> Starting findall with regex"

	data = re.findall(regex, f.read())

	node_list = []
	element_n = 1

	for element in data:
		node = dict()
		node['element_n'] = element_n
		explore_n = element[0]
		node['explore_n'] = explore_n

		if element[2] != '': # Check if a plan exists
			# Check if replay was needed:
			if element[1] != '':
				node['replay'] = element[1]
				replay = '** Replay: ' + element[1] + '\n'
			else:
				replay = ''

			node['plan'] = element[2]
			# This regex will give back a list of tuples, where the first
			# element is '{"\d+",\d+}' and the second element is the second \d+
			before_nodes_regex = "(\{\"[\d.]+\",(\d+)\})"
			before_nodes = re.findall(before_nodes_regex, element[3])
			# Only the second \d+ will be used
			node['before'] = [int(n[1]) for n in before_nodes]
			node['selected'] = element[4]
			node['pick_next'] = element[5]
			node['picked'] = element[6]
			# TODO: Check for color. Make children look similar to parents?

			# Replace every " for \" in the texts
			plan = re.sub('"', '\\"', element[2])
			happened = re.sub('"', '\\"', element[3])
			selected = re.sub('"', '\\"', element[4])
			pick_next = re.sub('"', '\\"', element[5])
			picked = re.sub('"', '\\"', element[6])

			label = '"Explore ' + explore_n + " | element " +\
					str(element_n) + '\\n' +\
					replay +\
					'~ ' + plan + '\\n' +\
					'~ ' + happened + '\\n' +\
					'~ ' + selected + '\\n' +\
					'~ ' + pick_next + '\\n' +\
					'~ ' + picked+'"'
			node_dot_text = "// Explore " + str(element_n) + "\n" +\
							str(element_n) + " [label = " + label + "];\n"

			node['text'] = node_dot_text
		else:
			# Check if there was an error
			if element[8] == '':
				backtrack_info = element[7]
				node['backtrack'] = backtrack_info

				label = '"Explore ' + explore_n + " | element " +\
						str(element_n) + '\\n' +\
						'Backtrack set explored.'
				if backtrack_info != '':
					label += ' ' + backtrack_info
				label += '"'
				node_dot_text = "// Explore " + str(element_n) + "\n" +\
							str(element_n) + " [label = " + label + "];\n"
			else:
				error = element[8]
				node['error'] = error
				label = '"Explore ' + explore_n + " | element " +\
						str(element_n) + '\\n' +\
						'ERROR!\n' + error + '"'
				node_dot_text = "// Explore " + str(element_n) + "\n" +\
							str(element_n) + " [label = " + label + "];\n"

			node['text'] = node_dot_text
		node_list.append(node)
		element_n += 1

	return node_list

def create_clusters(node_list):
	# The tracks are separated with the adjacent elements
	connection_groups = []
	adjacent_list = []
	for node in node_list:
		if 'plan' in node: # Check if a plan exists
			adjacent_list.append(node)
		else:
			if adjacent_list != []:
				connection_groups.append(adjacent_list)
			adjacent_list = []
	return connection_groups

# Returned is a dict where the key is the element number and the value is a list
# of element numbers that are needed to create the key
def all_previous_connections(node_list):
	before_dict = dict()
	explore_element_dict = dict()

	for node in node_list:
		explore_n = node.get('explore_n')
		if 'plan' in node:
			element_n = node.get('element_n')
			explore_element_dict[int(explore_n)] = element_n
			prev_elem_list = []
			##print str(element_n) + ".get('before'): " + str(node.get('before'))
			for prev_explore in node.get('before'):
				prev_elem_list.append(explore_element_dict.get(prev_explore))
			##print "prev_elem_list" + str(prev_elem_list)
			before_dict[element_n] = prev_elem_list
		else: # The explore key is no longer related to the element number
			explore_element_dict.pop(explore_n, None)

	return before_dict

# String with the full content of the dot file
def dot_file_content(node_list):
	node_dot_list = ""
	for node in node_list:
		if 'plan' in node: # Only show nodes with a plan
			node_dot_list += node.get('text')
	#debug(node_dot_list)
	node_dot_list_str = str(node_dot_list)

	node_clusters = create_clusters(node_list)

	# Create the dot clusters
	cluster_info = ""
	cluster_n = 1
	for group in node_clusters:
		cluster_info += 'subgraph cluster_'+str(cluster_n) +' {\n' +\
						'label = "Track ' + str(cluster_n) + '";\n' +\
						'color = invis;\n'
		first_node = True
		for node in group:
			# A straight invisible line connecting all nodes is needed to
			# correctly align them.
			if not first_node:
				cluster_info += ' -> '
			else:
				first_node = False
			cluster_info += str(node.get('element_n'))
		# Check how a track ends
		ending_node = node_list[group[-1].get('element_n')]
		# The high weight is added to make a straight line of nodes
		cluster_node_style = ' [weight=1000];\n'
		if 'backtrack' in ending_node:
			ending = ending_node.get('backtrack')
			if ending == "DEADLOCK":
				cluster_info += ' -> lock_' + str(cluster_n)
				cluster_info += cluster_node_style
				cluster_info += 'lock_' + str(cluster_n) +\
				' [image="marmalade_lock.png", label="", style=invisible];\n'
			else:
				cluster_info += ' -> ok_' + str(cluster_n)
				cluster_info += cluster_node_style
				cluster_info += 'ok_' + str(cluster_n) +\
					' [image="marmalade_checkmark.png",' +\
					' label="", style=invisible];\n'
		elif 'error' in ending_node:
			cluster_info += ' -> bad_' + str(cluster_n)
			cluster_info += cluster_node_style
			cluster_info += 'bad_' + str(cluster_n) +\
				' [image="marmalade_cross.png",' +\
				' label="", style=invisible];\n'
		else:
			cluster_info += ' -> ok_' + str(cluster_n)
			cluster_info += cluster_node_style
			cluster_info += 'ok_' + str(cluster_n) +\
				' [image="marmalade_checkmark.png",' +\
				' label="", style=invisible];\n'
		cluster_info += '}\n\n'
		cluster_n = cluster_n + 1

	# # Visualize each previous connection to every node
	# connection_list = ""
	# for elem, prev_list in all_previous_connections(node_list).iteritems():
	# 	if prev_list: # If the previous list of nodes is not empty
	# 		if len(prev_list) > 1:
	# 			#label_text = str(prev_list) + ' => ' + str(elem)
	# 			label_text = ''
	# 		else:
	# 			label_text = ''
	# 		for prev_elem in prev_list:
	# 			connection_list += str(prev_elem) + ' -> ' + str(elem) +\
	# 								' [label = "' + label_text + '"];\n'

	# Show backtrack arrow:
	connection_list = ""
	explore_element_dict = dict()
	for group in node_clusters:
		first_element_n = group[0].get('element_n')
		if first_element_n > 1:
			first_explore_n = int(group[0].get('explore_n'))
			prev_explore = str(first_explore_n - 1)
			connection_list += str(explore_element_dict.get(prev_explore)) +\
					' -> ' + str(first_element_n) + ';\n'
		for node in group:
			explore_n = node.get('explore_n')
			element_n = node.get('element_n')
			explore_element_dict[explore_n] = element_n

	# Path where images are located:
	pathname = os.path.dirname(sys.argv[0])
	image_path = os.path.abspath(pathname)+'/img'

	file_info = 'digraph {\n' +\
				'//splines=line;//maybe?\n' +\
				'//splines=ortho;//maybe?\n' +\
				'//rankdir=LR;\n' +\
				'//rankdir=TB;\n' +\
				'//TODO: look at the following attributes:\n' +\
				'//TODO: rankstep\n' +\
				'//TODO: sep\n' +\
				'\n' +\
				'imagepath="'+image_path+'"\n' +\
				'node [shape=box]\n' +\
				'//node [shape=point]\n' +\
				'node [style="filled,rounded"]\n\n' +\
				 node_dot_list_str + '\n' +\
				 cluster_info +\
				 connection_list +\
				'}'
	return file_info

# Show the different blocks of information and what fields they contain
def print_nodes(node_list):
	n = 1
	text = ""
	for node in node_list:
		text += ">>> Info " + str(n)+":\n"
		m = 1
		for k, v in node.iteritems():
			if k == 'text':
				continue
			text += "> " + str(n)+"."+str(m) + " " + k + ': ' + str(v) + '\n'
			m = m + 1
		n = n + 1
	return text

if __name__ == "__main__":
	import re
	from sys import argv
	from os.path import isfile
	from subprocess import call

	if len(argv) == 1 or len(argv) > 3 or not isfile(argv[1]):
		print "Use: " + argv[0] + " conquerror_output_file [output format]"
	else:
		filename = argv[1]
		f = open(filename, 'r')
		node_list = file_to_node_list(f)
		f.close()
		debug(print_nodes(node_list))
		# TODO: Write parsed data to file?
		dot_file = filename + '.dot'
		f = open(dot_file, 'w')
		f.write(dot_file_content(node_list))
		f.close()
		output_file = filename + '_graph'
		# TODO: Check sfdp
		if len(argv) == 3:
			call(["dot", "-T"+argv[2], "-o" +output_file+'.'+argv[2], dot_file])
		else:
			call(["dot", "-Tpdf", "-o" + output_file + ".pdf", dot_file])
			# call(["dot", "-Tpng", "-o" + output_file + ".png", dot_file])
		print "Graph generated"
