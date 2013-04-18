#!/usr/bin/python2
import os,sys

# TODO: Color difference with spawns?

# DEBUG = True
DEBUG = False

def debug(info):
	if DEBUG:
		print info

def file_to_node_list(f):
	regex = "(?:(\d+): " +\
					"(?:" +\
						"(?:(action) :: (.+))" +\
					"|" +\
						"(?:(backtrack) :: (\w+))" +\
					"|" +\
						"(error)" +\
					"|" +\
						"(cycle)" +\
					"))"
	# print ">>>> Starting findall with regex"

	data = re.findall(regex, f.read())

	node_list = []
	element_n = 1

	for element in data:
		node = dict()
		node['element_n'] = element_n
		explore_n = element[0]
		node['explore_n'] = explore_n

		if element[1] == 'action': # Check if an action was taken
			node['action'] = element[2]
			# TODO: Check for color. Make children look similar to parents?

			# Replace every " for \" in the texts
			action = re.sub('"', '\\"', element[2])

			label = '"Explore ' + explore_n + " | element " +\
					str(element_n) + '\\n' + action + '"'
			node_dot_text = "// Explore " + str(element_n) + "\n" +\
							str(element_n) + " [label = " + label + "];\n"
		# Check if there was a backtrack
		elif element[3] == 'backtrack':
			node['backtrack'] = element[4]

			label = '"Explore ' + explore_n + " | element " +\
					str(element_n) + '\\n' +\
					'Backtrack set explored: ' + element[4] + '"'
			node_dot_text = "// Explore " + str(element_n) + "\n" +\
						str(element_n) + " [label = " + label + "];\n"
		# Check if there was an error
		elif element[5] == 'error':
			node['error'] = True

			label = '"Explore ' + explore_n + " | element " +\
					str(element_n) + '\\n' + 'ERROR!"'
			node_dot_text = "// Explore " + str(element_n) + "\n" +\
						str(element_n) + " [label = " + label + "];\n"
		# Check if there was a cycle
		elif element[6] == 'cycle':
			node['cycle'] = True
			label = '"Explore ' + explore_n + " | element " +\
					str(element_n) + '\\n' + 'CYCLE!"'
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
		if 'action' in node: # Check if an action was taken
			adjacent_list.append(node)
		else:
			if adjacent_list != []:
				connection_groups.append(adjacent_list)
			adjacent_list = []
	return connection_groups

# String with the full content of the dot file
def dot_file_content(node_list):
	node_dot_list = ""
	for node in node_list:
		if 'action' in node: # Only show nodes with an action
			node_dot_list += node.get('text')
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
		if ('backtrack' in ending_node and
				ending_node.get('backtrack') != 'normal'):
			cluster_info += ' -> lock_' + str(cluster_n)
			cluster_info += cluster_node_style
			cluster_info += 'lock_' + str(cluster_n) +\
			' [image="marmalade_lock.png", label="", style=invisible];\n'
		elif 'error' in ending_node:
			cluster_info += ' -> bad_' + str(cluster_n)
			cluster_info += cluster_node_style
			cluster_info += 'bad_' + str(cluster_n) +\
				' [image="marmalade_cross.png",' +\
				' label="", style=invisible];\n'
		elif 'cycle' in ending_node:
			cluster_info += ' -> cycle_' + str(cluster_n)
			cluster_info += cluster_node_style
			cluster_info += 'cycle_' + str(cluster_n) +\
				' [image="marmalade_cycle.png",' +\
				' label="", style=invisible];\n'
		else:
			cluster_info += ' -> ok_' + str(cluster_n)
			cluster_info += cluster_node_style
			cluster_info += 'ok_' + str(cluster_n) +\
				' [image="marmalade_checkmark.png",' +\
				' label="", style=invisible];\n'
		cluster_info += '}\n\n'
		cluster_n = cluster_n + 1

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

	# //splines=line;//maybe?
	# //splines=ortho;//maybe?
	# //rankdir=LR;
	# //rankdir=TB;
	# //TODO: look at the following attributes:
	# //TODO: rankstep
	# //TODO: sep
	file_info = 'digraph {\n' +\
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
		output_file = filename # + '_graph'
		# TODO: Check sfdp
		if len(argv) == 3:
			call(["dot", "-T"+argv[2], "-o" +output_file+'.'+argv[2], dot_file])
		else:
			call(["dot", "-Tpdf", "-o" + output_file + ".pdf", dot_file])
			# call(["dot", "-Tpng", "-o" + output_file + ".png", dot_file])
		print "Graph generated"
