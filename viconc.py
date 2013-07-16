#!/usr/bin/python2
##/usr/bin/env python2
import os,sys

# TODO: Color difference with spawns?

# DEBUG = True
DEBUG = False

def debug(info):
	if DEBUG:
		print info

def file_to_node_list(f):
	regex = '(?:(\d+): ' +\
					'(?:' +\
						'(?:(action) :: "(.+)")' +\
					'|' +\
						'(?:(backtrack) :: (\w+))' +\
					'|' +\
						'(error)' +\
					'|' +\
						'(cycle)' +\
					'))'
	# print ">>>> Starting findall with regex"

	data = re.findall(regex, f.read())

	node_list = []
	event_n = 1
	action_n = 1

	for event in data:
		node = dict()
		node['event_n'] = event_n
		explore_n = event[0]
		node['explore_n'] = explore_n

		if event[1] == 'action': # Check if an action was taken
			node['action'] = event[2]
			# Replace every " for \" in the texts, if not preceded by \
			action = re.sub('[^\\\]"', '\\"', event[2])
			label = '"Explore ' + explore_n + " | Action " +\
					str(action_n) + '\\n' + action + '"'
			node_dot_text = str(event_n) + " [label = " + label + "];\n"
			action_n += 1
		# Check if there was a backtrack
		elif event[3] == 'backtrack':
			node['backtrack'] = event[4]
			label = '"Explore ' + explore_n + " | event " +\
					str(event_n) + '\\n' +\
					'Backtrack set explored: ' + event[4] + '"'
			node_dot_text = str(event_n) + " [label = " + label + "];\n"
		# Check if there was an error
		elif event[5] == 'error':
			node['error'] = True
			label = '"Explore ' + explore_n + " | event " +\
					str(event_n) + '\\n' + 'ERROR!"'
			node_dot_text = "// Explore " + str(event_n) + "\n" +\
						str(event_n) + " [label = " + label + "];\n"
		# Check if there was a cycle
		elif event[6] == 'cycle':
			node['cycle'] = True
			label = '"Explore ' + explore_n + " | event " +\
					str(event_n) + '\\n' + 'CYCLE!"'
			node_dot_text = "// Explore " + str(event_n) + "\n" +\
						str(event_n) + " [label = " + label + "];\n"

		node['text'] = node_dot_text
		node_list.append(node)
		event_n += 1

	return node_list

def create_clusters(node_list):
	# The tracks are separated with the adjacent events
	connection_groups = []
	adjacent_list = []
	created_cluster = False
	for node in node_list:
		if 'action' in node: # Check if an action was taken
			adjacent_list.append(node)
			created_cluster = False
		else:
			if adjacent_list != []:
				connection_groups.append(adjacent_list)
			adjacent_list = []
			created_cluster = True
	if not created_cluster:
		connection_groups.append(adjacent_list)
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
	# keep track of how they finish for chronological ordering:
	ending_cluster_nodes = []
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
			cluster_info += str(node.get('event_n'))
		# Check how a track ends
		last_node_n = group[-1].get('event_n')
		# The high weight is added to make a straight line of nodes
		cluster_node_style = '[weight=1000]'
		# Then the Concuerror was stopped by the user, a warning will show
		if last_node_n >= len(node_list):
			warning_image = "marmalade_warning.png"
			ending_name = 'warning_' + str(cluster_n)
			ending_image = warning_image
		else:
			ending_node = node_list[last_node_n]
			if ('backtrack' in ending_node and
					ending_node.get('backtrack') != 'normal'):
				if ending_node.get('backtrack') == 'deadlock':
					lock_image = "marmalade_lock.png"
					ending_name = 'lock_' + str(cluster_n)
					ending_image = lock_image
				elif ending_node.get('backtrack') == 'sleep_set_block':
					# warning_image = "marmalade_checkmark.png"
					warning_image = "marmalade_warning.png"
					ending_name = 'sleep_set_block_' + str(cluster_n)
					ending_image = warning_image
			elif 'error' in ending_node:
				cross_image = "marmalade_cross.png"
				ending_name = 'bad_' + str(cluster_n)
				ending_image = cross_image
			elif 'cycle' in ending_node:
				cycle_image = "marmalade_cycle.png"
				ending_name = 'cycle_' + str(cluster_n)
				ending_image = cycle_image
			else:
				checkmark_image = "marmalade_checkmark.png"
				ending_name = 'ok_' + str(cluster_n)
				ending_image = checkmark_image
		cluster_info += ' -> ' + ending_name + ' ' + cluster_node_style + ';\n'
		cluster_info += ending_name +' [image="'+ending_image+'"' +\
				', label="", style=invisible];\n'
		cluster_info += '}\n\n'
		cluster_n = cluster_n + 1
		ending_cluster_nodes.append(ending_name)

	# Show arrow to interleavings after a backtrack:
	connection_list = "//Interleavings after backtrack\n"
	explore_event_dict = dict()
	for group in node_clusters:
		first_event_n = group[0].get('event_n')
		if first_event_n > 1:
			first_explore_n = int(group[0].get('explore_n'))
			prev_explore = str(first_explore_n - 1)
			connection_list += str(explore_event_dict.get(prev_explore)) +\
					' -> ' + str(first_event_n) + ';\n'
		for node in group:
			explore_n = node.get('explore_n')
			event_n = node.get('event_n')
			explore_event_dict[explore_n] = event_n

	# Correct the graph so the track numbers are shown from left to right
	chronological_ordering = ""
	if len(node_clusters) > 0:
		top_order_nodes = []
		bottom_order_nodes = []
		chronological_ordering = "\n//Chronological track ordering\n"
		chronological_ordering += 'node[shape=none, width=0, height=0, label=""];\n'
		chronological_ordering += 'edge[dir=none, style=invisible];\n'
		for i in range(1, len(node_clusters) + 1):
			top_order_nodes.append('t'+str(i))
			bottom_order_nodes.append('b'+str(i))
		top_rank_text = '{rank=same;'
		bottom_rank_text = '{rank=same;'
		for i in range(0, len(node_clusters)):
			top_rank_text += top_order_nodes[i]
			bottom_rank_text += bottom_order_nodes[i]
			if i != len(node_clusters)-1:
				top_rank_text += ','
				bottom_rank_text += ','
			else:
				top_rank_text += '}\n'
				bottom_rank_text += '}\n'
		for i in range(0, len(node_clusters)):
			top_rank_text += top_order_nodes[i]
			bottom_rank_text += bottom_order_nodes[i]
			if i != len(node_clusters)-1:
				top_rank_text += ' -> '
				bottom_rank_text += ' -> '
			else:
				top_rank_text += ';\n'
				bottom_rank_text += ';\n'
		# First the top hidden nodes are displayed in the dot file
		chronological_ordering += top_rank_text
		for i in range(0, len(node_clusters)):
			chronological_ordering += top_order_nodes[i] + ' -> ' +\
					str(node_clusters[i][0].get('event_n')) + ';\n'
		# After, the bottom hidden nodes are displayed in the dot file
		chronological_ordering += bottom_rank_text
		for i in range(0, len(ending_cluster_nodes)):
			chronological_ordering += str(ending_cluster_nodes[i]) + ' -> ' +\
					bottom_order_nodes[i] + ';\n'

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
				'//splines=ortho;\n' +\
				'//nodesep=1;\n' +\
				'//ranksep=equally;\n' +\
				'//node [shape=plaintext]\n' +\
				'node [shape=box]\n' +\
				'//node [shape=point]\n' +\
				'node [style="filled,rounded"]\n' +\
				'edge [arrowhead="vee"]\n\n' +\
				'// Interaction information nodes\n' +\
				 node_dot_list_str + '\n' +\
				 cluster_info +\
				 connection_list +\
				 chronological_ordering +\
				'\n' +\
				'}\n'
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
		dot_file = filename + '.dot'
		f = open(dot_file, 'w')
		f.write(dot_file_content(node_list))
		f.close()
		output_file = filename
		# TODO: Check sfdp
		if len(argv) == 3:
			call(["dot", "-T"+argv[2], "-o" +output_file+'.'+argv[2],
				dot_file])
		else:
			call(["dot", "-Tpdf", "-o" + output_file + ".pdf", dot_file])
			# call(["dot", "-Tpng", "-o" + output_file + ".png", dot_file])
		print "Finished"
