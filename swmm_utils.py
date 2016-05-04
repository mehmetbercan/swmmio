#Utilities and such for SWMMIO processing
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps
from time import strftime
import os
import numpy as np
import matplotlib.path as mplPath
from matplotlib.transforms import BboxBase
import pickle
import json

#contants
sPhilaBox = 	((2683629, 220000), (2700700, 231000))
sPhilaSq =		((2683629, 220000), (2700700, 237071))
sPhilaSm1 = 	((2689018, 224343), (2691881, 226266))
sPhilaSm2 = 	((2685990, 219185), (2692678, 223831))
sPhilaSm3 = 	((2688842, 220590), (2689957, 221240))
sPhilaSm4 = 	((2689615, 219776), (2691277, 220738))
sPhilaSm5 = 	((2690303, 220581), (2690636, 220772))
sm6 = 			((2692788, 225853), (2693684, 226477))
chris = 		((2688798, 221573), (2702834, 230620))
nolibbox= 		((2685646, 238860),	(2713597, 258218))
mckean = 		((2691080, 226162),	(2692236, 226938))
d70 = 			((2694096, 222741),	(2697575, 225059))
ritner_moyamen =((2693433, 223967),	(2694587, 224737))
morris_10th = 	((2693740, 227260),	(2694412, 227693))
study_area = 	((2680283, 215575), (2701708, 235936))
dickenson_7th = ((2695378, 227948), (2695723, 228179))
packer_18th = 	((2688448, 219932), (2691332, 221857))

#COLOR DEFS
red = 		(250, 5, 5)
blue = 		(5, 5, 250)
shed_blue = (0,169,230)
white =		(250,250,240)
black = 	(0,3,18)
lightgrey = (235, 235, 225)
grey = 		(100,95,97)
park_green = (115, 178, 115)
green = 	(115, 220, 115)
water_grey = (130, 130, 130)
def getFeatureExtent(feature, where="SHEDNAME = 'D68-C1'", geodb=r'C:\Data\ArcGIS\GDBs\LocalData.gdb'):
	
	import arcpy
	features = os.path.join(geodb, feature)
	for row in arcpy.da.SearchCursor(features, ["SHAPE@"], where_clause=where):
		
		#extent = row[0].extent
		#xy1,  xy2 =(extent.XMin, extent.YMin), (extent.XMax, extent.YMax)
		#return xy1, xy2
		#return row
		for part in row[0]:
			xy1,  xy2 =(part[0].X, part[0].Y), (part[1].X, part[1].Y)
			
			print xy1, xy2
			#print part
			
#FUNCTIONS
def traceFromNode(model, startNode, mode='up'):
	
	#nodes = model.organizeNodeData(bbox)['nodeDictionaries']
	#links = model.organizeConduitData(bbox)['conduitDictionaries']
	inp = model.inp
	conduitsDict = inp.createDictionary("[CONDUITS]")
	storagesDict = inp.createDictionary("[STORAGE]")
	junctionsDict = inp.createDictionary("[JUNCTIONS]")
	outfallsDict = inp.createDictionary("[OUTFALLS]")
	allNodesDict = merge_dicts(storagesDict, junctionsDict, outfallsDict)
	
	tracedNodes = []
	tracedConduits = []
	
	#recursive function to trace upstream
	def trace (nodeID):
		#print "tracing from {}".format(nodeID)
		for conduit, data in conduitsDict.iteritems():
			
			conduitUpNodeID = conduitDnNodeID = None
			if len(data) >= 1:
				#not sure why i need to do this check, but it prevents an indexing error on some
				conduitUpNodeID = data[0]
				conduitDnNodeID = data[1]
				
			if mode=='down' and conduitUpNodeID == nodeID and conduit not in tracedConduits:
				#conduit not in traced conduits to prevent duplicates for some reason					
				#grab its dnstream node ID
				tracedConduits.append(conduit)
				tracedNodes.append(conduitDnNodeID)
				trace(conduitDnNodeID)
			
			if mode == 'up' and conduitDnNodeID == nodeID and conduit not in tracedConduits:
				#conduit not in traced conduits to prevent duplicates for some reason
				#this conduit is upstream of current node
				#grab its upstream node ID
				tracedConduits.append(conduit)
				tracedNodes.append(conduitUpNodeID)
				trace(conduitUpNodeID)
			
	#kickoff the trace
	print "Starting trace {0} from {1}".format(mode, startNode)
	trace(startNode)
	
	return {'nodes':tracedNodes, 'conduits':tracedConduits}

def randAlphaNum(n=6):
	import random
	chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
	return ''.join(random.choice(chars) for i in range(n))

def pointIsInBox (bbox, point):
		
		#pass a lower left (origin) and upper right tuple representing a box,
		#and a tuple point to be tested
		
		LB = bbox[0]
		RU = bbox[1]
		
		x = point[0]
		y = point[1]
	
		if x < LB[0] or x >  RU[0]:
			return False
		elif y < LB[1] or y > RU[1]:
			return False
		else:
			return True

def pipeLengthPlanView(upstreamXY, downstreamXY):
	
	#return the distance (units based on input) between two points
	x1 = float(upstreamXY[0])
	x2 = float(downstreamXY[0])
	y1 = float(upstreamXY[1])
	y2 = float(downstreamXY[1])
	
	return math.hypot(x2 - x1, y2 - y1)
def pipeProfileLengthTransform(planLength, upstreamEl, downstreamEl, xTrans, yTrans):
	
	#tranform a pipe legth in x and y direction via its components
	
	ycomponent = upstreamEl - downstreamEl 
	newXComponent = planLength * xTrans
	newYComponent = ycomponent * yTrans
	
	return math.hypot(newXComponent, newYComponent)
def getX2(y1, y2, length, x1=0):
	
	#return the x2 coordinate given y1, y2, the line segment length, and x0
	
	a = y2 - y1
	c = length
	return math.sqrt(c*c - a*a) + x1
def merge_dicts(*dict_args):
    '''
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    '''
    result = {}
    for dictionary in dict_args:
		if dictionary:
			result.update(dictionary)
    return result
def greenRedGradient(x, xmin, xmax):
	
	range = xmax - xmin
	scale = 255 / range
	
	x = min(x, xmax) #limit any vals to the prescribed max
	
	#print "range = " + str(range)
	#print "scale = " + str(scale)
	r = int(round(x*scale))
	g = int(round(255 - x*scale))
	b = 0
	
	return (r, g, b)
def greyRedGradient(x, xmin, xmax):
	
	range = xmax - xmin
	
	rMin = 100
	bgMax = 100
	rScale = (255 - rMin) / range
	bgScale = (bgMax) / range
	x = min(x, xmax) #limit any vals to the prescribed max
	
	
	#print "range = " + str(range)
	#print "scale = " + str(scale)
	r = int(round(x*rScale + rMin ))
	g = int(round(bgMax - x*bgScale))
	b = int(round(bgMax - x*bgScale))
	
	return (r, g, b)
def greyGreenGradient(x, xmin, xmax):
	
	range = xmax - xmin
	
	gMin = 100
	rbMax = 100
	gScale = (255 - gMin) / range
	rbScale = (rbMax) / range
	x = min(x, xmax) #limit any vals to the prescribed max
	
	
	#print "range = " + str(range)
	#print "scale = " + str(scale)
	r = int(round(rbMax - x*rbScale))
	g = int(round(x*rbScale + gMin ))
	b = int(round(rbMax - x*rbScale))
	
	return (r, g, b)

def col2RedGradient(x, xmin, xmax, startCol=lightgrey):
	
	range = xmax - xmin
	
	rMin = startCol[0]
	gMax = startCol[1]
	bMax = startCol[2]
	
	rScale = (255 - rMin) / range
	gScale = (gMax) / range
	bScale = (bMax) / range
	x = min(x, xmax) #limit any vals to the prescribed max
	
	
	#print "range = " + str(range)
	#print "scale = " + str(scale)
	r = int(round(x*rScale + rMin ))
	g = int(round(gMax - x*gScale))
	b = int(round(bMax - x*bScale))
	
	return (r, g, b)

	#lightgrey = (235, 235, 225)

def blueRedGradient(x, xmin, xmax):
	
	range = xmax - xmin
	scale = 255 / range
	
	x = min(x, xmax) #limit any vals to the prescribed max
	
	#print "range = " + str(range)
	#print "scale = " + str(scale)
	r = int(round(x*scale))
	g = 0
	b = int(round(255 - x*scale))
	
	return (r, g, b)

def elementChange(elementData, parameter='maxflow'):
	
	#with a joined dictionary item, returns change from existing to proposed
	
	proposedVal = elementData['proposed'].get(parameter, 0.0)
	existingVal = elementData['existing'].get(parameter, 0.0)
	
	return proposedVal - existingVal
	
def subsetConduitsInBoundingBox(conduitsDict, boundingBox):
	
	newDict = {}
	for conduit, conduitData in conduitsDict.iteritems():
		if 'existing' and 'proposed' in conduitData:
			#then we have a "compare" dictionary, must drill down further, use proposed
			coordPair = conduitData['proposed']['coordinates']
		else: 
			coordPair = conduitData['coordinates']
		
		if boundingBox and (not pointIsInBox(boundingBox, coordPair[0]) or not pointIsInBox(boundingBox, coordPair[1])):
			#ship conduits who are not within a given boudning box
			continue
		
		newDict.update({conduit:conduitData})
	
	return 	newDict

def subsetElements(model, type='node', key='floodDuration', min=0.083, max=99999, bbox=None, pair_only=False):
	#return a subset of a dictionary of swmm elements based on a value 
	
	if type=='node':
		elems = model.organizeNodeData(bbox)['nodeDictionaries']
		
	elif type=='conduit':
		elems = model.organizeConduitData(bbox)['conduitDictionaries']
	else: return []
	
	if pair_only:
		#only return the element and the value being filtered on 
		subset = {k:v[key] for (k,v) in elems.items() if v[key] >= min and v[key] < max}
	else:
		subset = {k:v for (k,v) in elems.items() if v[key] >= min and v[key] < max}
	
	return subset

	 
def parcel_flood_duration(model, parcel_features, threshold=0.083,  bbox=None, gdb=r'C:\Data\ArcGIS\GDBs\LocalData.gdb', export_table=False):
	
	#return a dictionary of each parcel ID with averagre flood duration
	
	#grab the list of flooded nodes, and create the dictionary of parcels linked to node IDs
	flooded_nodes = subsetElements(model, min=threshold, bbox=bbox, pair_only=True)
	parcels_dict = parcel_dict_from_joined_feature(parcel_features, where = None, gdb=gdb, bbox=bbox)
	
	#return parcels_dict
	#calculate average flood duration for each parcel
	parcels_flooded_count = 0.0
	for parcel, parcel_data in parcels_dict.iteritems():
	
		associated_nodes = parcel_data['nodes'] #associated nodes
		
		if len(associated_nodes) > 0:
			
			total_parcel_flood_dur = 0.0
			for node in associated_nodes:
				#look up the flood duration
				node_duration = flooded_nodes.get(node, 0)
				total_parcel_flood_dur += node_duration
			
			avg_flood_duration = total_parcel_flood_dur/len(associated_nodes)
			parcel_data.update({'avg_flood_duration':avg_flood_duration})
			
			if avg_flood_duration > 0:
				parcels_flooded_count += 1.0
	
	parcels_count = len(parcels_dict)
	parcels_flooded_fraction = parcels_flooded_count/parcels_count
	
	results = {
				'parcels_flooded_count':parcels_flooded_count, 
				'parcels_count':parcels_count,
				'parcels_flooded_fraction':parcels_flooded_fraction,
				'parcels':parcels_dict
				}
	print 'Found {0} ({1}%) parcels, of {2} total, with flooding above {3} hours.'.format(parcels_flooded_count, round(parcels_flooded_fraction*100), parcels_count, threshold)
	return results
	 
def parcelsFlooded(model, threshold = 0.083, bbox=None, shiftRatio=None, width=1024):

	#return list of nodes with flood duration above threshold 
	flooded_nodes = subsetElements(model, min=threshold, bbox=bbox)
	print '{} flooded nodes found'.format(len(flooded_nodes))
	
	#return sheds that contain these floode nodes (room for optimization here, don't need to rescan the arcpy search cursor every time...)
	sheds = shape2Pixels("detailedsheds", where=None, targetImgW=width, shiftRatio=shiftRatio, bbox=bbox)['geometryDicts']
	parcels = shape2Pixels("parcels3", where=None, targetImgW=width, shiftRatio=shiftRatio, bbox=bbox)
	
	imgSize = parcels['imgSize']
	parcels = parcels['geometryDicts']
	print 'Processing {0} sheds and {1} parcels'.format(len(sheds), len(parcels))
	
	sheds_with_flooded_nodes = {}
	parcels_flooded = {}
	for shed, data in sheds.iteritems():
		#create a path object and test if contains any flooded nodes
		coords = data['coordinates']
		shed_path = mplPath.Path(coords) #matplotlib Path object 
		shed_bbox = shed_path.get_extents()

		floodDurationSum = 0.0 #to calc the average duration in the shed
		flood_nodes_in_shed = {}
		for node, data in flooded_nodes.iteritems():
			
			
			x,y = data['coordinates']
			if shed_bbox.contains(x,y):
				#check first if shed bounding box contains point, if not, move on. 
				#If yes, allow this more detailed search
				if shed_path.contains_point(data['coordinates']): #maybe used contains_points for efficiency
					
					#we found a shed with flooding
					flood_nodes_in_shed.update({node:data['floodDuration']})
					
					floodDurationSum += data['floodDuration']
				
		#build a dictionary containing each shed with flooded nodes, 
		#containing a dictionary of each node with hours flooded
		if flood_nodes_in_shed:
			avgDuration = floodDurationSum / float(len(flood_nodes_in_shed))
			
			sheds_with_flooded_nodes.update({shed:flood_nodes_in_shed})
			
			#find the parcels that intersect
			for parcel, data in parcels.iteritems():
				coords = data['coordinates']
				parcel_path = mplPath.Path(coords) #matplotlib Path object 
				parcel_bbox = parcel_path.get_extents()
			
				if BboxBase.intersection(shed_bbox, parcel_bbox):
					#check first if shed bounding box intersects parcel boudning box, if not, move on
					if shed_path.intersects_path(parcel_path):
						
						parcels_flooded.update({parcel:{'shed':shed,'avgerage_duration':avgDuration, 'flooded_nodes':flood_nodes_in_shed, 'draw_coordinates':data['draw_coordinates']}})
						#return parcels_flooded
	
	print 'Found {0} sheds and {1} parcels with flooding above {2} hours.'.format(len(sheds_with_flooded_nodes), len(parcels_flooded), threshold)
	return {'sheds':sheds_with_flooded_nodes, 'parcels':parcels_flooded, 'imgSize':imgSize}


def parcel_dict_from_joined_feature(feature, cols = ["PARCELID", "OUTLET", "SUBCATCH", "SHAPE@"], bbox=None, where="shedFID = 1238", gdb=r'C:\Data\ArcGIS\GDBs\LocalData.gdb'):
	
	#create diction with keys for each parcel, and sub array containing associated nodes
	features = os.path.join(gdb, feature)
	import arcpy
	parcels = {}
	for row in arcpy.da.SearchCursor(features, cols, where_clause=where):
		
		#first check if parcel is in bbox
		jsonkey = 'rings' #for arc polygons
		geometrySections = json.loads(row[3].JSON)[jsonkey]
		parcel_in_bbox=True #assume yes first
		for i, section in enumerate(geometrySections):
			#check if part of geometry is within the bbox, skip if not
			if bbox and len ( [x for x in section if pointIsInBox(bbox, x)] ) == 0:
				parcel_in_bbox=False #continue #skip this section if none of it is within the bounding box
			
		if not parcel_in_bbox:
			continue #skip if not in bbox
		
		PARCELID = str(row[0])
		if PARCELID in parcels:
			#append to existing array
			parcels[PARCELID]['nodes'].append(row[1])
			parcels[PARCELID]['sheds'].append(row[2])
		else:
			#new parcel id found
			
			parcels.update({ PARCELID:{'nodes':[row[1]], 'sheds':[row[2]] }} )
			
	return parcels
	
def shape2Pixels(feature, cols = ["OBJECTID", "SHAPE@"],  where="SHEDNAME = 'D68-C1'", shiftRatio=None, targetImgW=1024, bbox=None, gdb=r'C:\Data\ArcGIS\GDBs\LocalData.gdb'):
	
	#take data from a geodatabase and organize in a dictionary with coordinates and draw_coordinates
	
	
	import arcpy
	
	features = os.path.join(gdb, feature)
	geometryDicts = {}
	for row in arcpy.da.SearchCursor(features, cols, where_clause=where):
		
		try:
			#detect what shape type this is
			geomType = row[1].type
			jsonkey = 'rings' #default for polygons, for accessing polygon vert coords
			if geomType == 'polyline': 
				jsonkey = 'paths'
		
		
			geometrySections = json.loads(row[1].JSON)[jsonkey] # an array of parts
			#geomArr = json.loads(row[1].JSON)[jsonkey][0] #(assumes poly has one ring)
			
			for i, section in enumerate(geometrySections):
				
				#check if part of geometry is within the bbox, skip if not
				if bbox and len ( [x for x in section if pointIsInBox(bbox, x)] ) == 0:
					continue #skip this section if none of it is within the bounding box
				
				id = str(row[0])				
				if len(geometrySections) > 1:
					id = str(row[0]) + "." + str(i)
					
				geometryDict = {'coordinates':section, 'geomType':geomType}	
				#geometryDicts.update({id:{'coordinates':geomArr}})
			
				#add any other optional cols, starting at 3rd col item
				for j, col in enumerate(cols[2:]): 
					col_data = str(row[j+2])
					geometryDict.update({col:col_data})
			
				geometryDicts.update({id:geometryDict})
			
		except:
			"prob with ", row[0]
	
	#find mins and maxs
	maxX = maxY = 0.0 #determine current width prior to ratio transform
	minX = minY = 99999999.0
	if not bbox:
		#review all points of the polygon to find min of all points
		for geom, geomData in geometryDicts.iteritems():
			for seg in geomData['coordinates']:
				minX = min(minX, seg[0])
				minY = min(minY, seg[1])
				maxX = max(maxX, seg[0])
				maxY = max(maxY, seg[1])
		bbox = [(minX, minY),(maxX, maxY)]
	
	#can probably get rid of these, if polygons are always secondary to the model drawing stuff (in which these params should be defined)
	height = float(bbox[1][1]) - float(bbox[0][1])
	width = float(bbox[1][0]) - float(bbox[0][0])
	shiftRatio = float(targetImgW / width) # to scale down from coordinate to pixels
	
	for geom, geomData in geometryDicts.iteritems():
		drawCoords = []
		for coord in geomData['coordinates']:
			
			drawCoord = coordToDrawCoord(coord, bbox, shiftRatio)
			drawCoords.append(drawCoord)
		geomData.update({'draw_coordinates':drawCoords})
	
	imgSize = (width*shiftRatio, height*shiftRatio)
	imgSize = [int(math.ceil(x)) for x in imgSize] #convert to ints
	
	polyImgDict = {'geometryDicts':geometryDicts, 'imgSize':imgSize , 'boundingBox': bbox, 'shiftRatio':shiftRatio }
	
	return polyImgDict
	
def convertCoordinatesToPixels(elementDict, targetImgW=1024, bbox=None, shiftRatio=None):
	
	#adds a dictionary to each conduit or node dict called
	#'draw_coordinates' which is a two part tuple, xy1, xy2
	
	if not bbox:
		#start by determining the max and min coordinates in the whole model
		maxX = maxY = 0.0 #determine current width prior to ratio transform
		minX = minY = 99999999
		for element, elementData in elementDict.iteritems():
			
			if 'existing' and 'proposed' in elementData:
				#then we have a "compare" dictionary, must drill down further, use proposed
				coordPair = elementData['proposed']['coordinates']
			else: 
				coordPair = elementData['coordinates']
			
			
			if type(coordPair[0]) is list:
				#loop for elements with multiple coordinates (lines)
				#each coordinate is a list 
				for coord in coordPair: 
					minX = min(minX, coord[0])
					minY = min(minY, coord[1])
					maxX = max(maxX, coord[0])
					maxY = max(maxY, coord[1])
			
			else:
				minX = min(minX, coordPair[0])
				minY = min(minY, coordPair[1])
				maxX = max(maxX, coordPair[0])
				maxY = max(maxY, coordPair[1])
			
		bbox = [(minX, minY),(maxX, maxY)]
	
	height = float(bbox[1][1]) - float(bbox[0][1])
	width = float(bbox[1][0]) - float(bbox[0][0])
	if not shiftRatio:
		shiftRatio = float(targetImgW / width) # to scale down from coordinate to pixels
	
	print "reg shift ratio = ", shiftRatio
	for element, elementData in elementDict.iteritems():
		
		if 'existing' and 'proposed' in elementData:
			#then we have a "compare" dictionary, must drill down further, use proposed
			coordPair = elementData['proposed']['coordinates']
		else: 
			coordPair = elementData['coordinates']
		
		
		drawcoords = []
		if type(coordPair[0]) is list:
			#loop for elements with multiple coordinates (lines)
			#each coordinate is a list 
			for coord in coordPair: 
				xy = coordToDrawCoord(coord, bbox, shiftRatio)
				drawcoords.append(xy)
		else:
			#zeroth index is not list, therefore coordPair is a single coord
			drawcoords = coordToDrawCoord(coordPair, bbox, shiftRatio)
			
		elementData.update({'draw_coordinates':drawcoords})
	
	imgSize = (width*shiftRatio, height*shiftRatio)
	imgSize = [int(math.ceil(x)) for x in imgSize] #convert to ints
	modelSizeDict = {'imgSize':imgSize, 'boundingBox': bbox, 'shiftRatio':shiftRatio }
	return modelSizeDict

def coordToDrawCoord(coordinates, bbox, shiftRatio):
	
	#convert single coordinate pair into the drawing space (pixels rather than cartesian coords)
	#given a cartesian bbox and shiftRatio
	
	#transform coords by normalizing by the mins, apply a ratio to 
	#produce the desired width pixel space 
	
	minX = float(bbox[0][0])
	minY = float(bbox[0][1])
	maxX = float(bbox[1][0])
	maxY = float(bbox[1][1])
		
	height = maxY - minY
	width = maxX - minX
	
	x =  (coordinates[0] - minX) * shiftRatio
	y =  (height - coordinates[1] + minY) * shiftRatio #subtract from height because PIL origin is in top right	
	
	return (x,y)

	
def circleBBox(coordinates, radius):
	#returns the bounding box of a circle given as centriod coordinate and radius
	x = coordinates[0] #this indexing is because other elements haev more than on coordinate (ulgy pls fix)
	y = coordinates[1]
	r = radius
	
	return (x-r, y-r, x+r, y+r)

def drawNode(id, nodeData, draw, options, rpt=None, dTime=None, xplier=1):
	
	color = (210, 210, 230) #default color 
	radius = 0 #aka don't show this node by default
	outlineColor = None 
	xy = nodeData['draw_coordinates']
	threshold = options['threshold']
	type = options['type']
	if dTime:
		
		data = rpt.returnDataAtDTime(id, dTime, sectionTitle="Node Results") 
		q = abs(float(data[2])) #absolute val because backflow
		floodingQ = float(data[3])
		HGL = float(data[5]) 
		
		if type=='flood':
			
			#node params
			if floodingQ > 1:
				radius = q/2 
				color = red #greenRedGradient(HGLup, 0, 15) #color
	
	elif 'existing' and 'proposed' in nodeData:
		#we're dealing with "compare" dictionary
		floodDurationChange = elementChange(nodeData, parameter='floodDuration')
		
		if floodDurationChange > 0 :
			#Flood duration increase
			radius = floodDurationChange*20
			color = red 
			
		if nodeData['existing'].get('floodDuration', 0) == 0 and nodeData['proposed'].get('floodDuration', 0) > 0:
			#new flooding found
			radius = floodDurationChange*20
			color = (250, 0, 250) #purple	
			outlineColor = (90, 90, 90)
		
	else:
		floodDuration = nodeData.get('floodDuration', 0)
		maxDepth = nodeData['maxDepth']
		maxHGL = nodeData['maxHGL']
	
		if type == 'flood':
			#if floodDuration > 0.08333:
			if floodDuration >= threshold:
				radius = floodDuration*3
				color = red
		
		if type == 'flood_color':
			radius = 3
			if floodDuration >= threshold:
				yellow = (221, 220, 0)
				color = col2RedGradient(floodDuration, 0, 1, startCol=yellow) #options['fill'](floodDuration, 0, 1+threshold)
			else:
				
				radius = 1
	
	radius *= xplier
	draw.ellipse(circleBBox(xy, radius), fill =color, outline=outlineColor)
	
def line_size(q, exp=1):
	return int(round(math.pow(q, exp)))

def drawConduit(id, conduitData, canvas, options, rpt=None, dTime = None, xplier = 1, highlighted=None):
	
	#Method for drawing (in plan view) a single conduit, given its RPT results 
	
	#default fill and size
	fill = (120, 120, 130)
	drawSize = 1
	coordPair = conduitData['draw_coordinates']
	type = options['type']
	#general method for drawing one conduit
	if rpt:
		#if an RPT is supplied, collect the summary data
		maxQPercent = conduitData['maxQpercent']
		q =  conduitData['maxflow']
		
		
		if maxQPercent !=0:
			capacity = q / maxQPercent
		else:
			capacity = 1
		stress = q / capacity
		
		if dTime:
			#if a datetime is provided, grab the specif flow data at this time
			data = rpt.returnDataAtDTime(id, dTime) #this is slow
			q = abs(float(data[2])) #absolute val because backflow	
			stress = q / capacity    #how taxed is the pipe
		
		remaining_capacity = capacity-q 
		#=================================
		#draw the conduit type as specifed
		#=================================		
		if type == "flow":
	
			fill = options['fill']
			drawSize = options['draw_size'](q, options['exp']) 
		
		if type == "flow_stress":
	
			fill = options['fill'](q*100, 0, capacity*175)
			drawSize = options['draw_size'](q, options['exp']) #int(round(math.pow(q, 0.67)))
				
		elif type == "stress":
			
			if maxQPercent >= 1:
				fill = options['fill'](q*100, 0, capacity*300) #greenRedGradient(q*100, 0, capacity*300)
				drawSize = options['draw_size'](stress*options['xplier'], options['exp']) #int(round(math.pow(stress*4, 1)))
			
		elif type == "capacity_remaining":						
			
			if remaining_capacity > 0:
				fill = (0, 100, 255)
				drawSize = int( round( math.pow(remaining_capacity, 0.8)))
		
		
			
			#drawSize = int( round(max(remaining_capacity, 1)*xplier) )
			
	elif 'existing' and 'proposed' in conduitData:
		#we're dealing with "compare" dictionary
		lifecycle = conduitData['lifecycle'] #new, chnaged, or existing conduit
		qChange = 	elementChange(conduitData, parameter='maxflow')
		upHGL = 	elementChange(conduitData, parameter='maxHGLUpstream')
		dnHGL = 	elementChange(conduitData, parameter='maxHGLDownstream')
		maxQperc = 	elementChange(conduitData, parameter='maxQpercent')
		avgHGL = (upHGL + dnHGL) / 2.0
		
		
		#FIRST DRAW NEW OR CHANGED CONDUITS IN A CLEAR WAY
		if lifecycle == 'new':
			fill = blue
			drawSize = min(10, conduitData['proposed']['geom1'])*3 
		
		if lifecycle == 'changed':
			fill = blue
			drawSize = min(50, conduitData['proposed']['geom1'])*3 	
		
		#IF THE CONDUITS IS 'EXISTING', DISPLAY SYMBOLOGY ACCORDINGLY (how things changed, etc)
		if lifecycle == 'existing':
			
			if type == 'compare_flow':
					
				if qChange > 0:
					fill = greyRedGradient(qChange, 0, 20)
					drawSize = int(round(math.pow(qChange, 1)))
				
				if qChange <= 0:
					fill = greyGreenGradient(abs(qChange), 0, 20)
					drawSize = int(round(math.pow(qChange, 1)))
				
			if type == 'compare_hgl':
				
				if avgHGL > 0:
					fill = greyRedGradient(avgHGL+15, 0, 20)
					drawSize = int(round(math.pow(avgHGL*5, 1)))
				
				if avgHGL <= 0:
					fill = greyGreenGradient(abs(avgHGL)+15, 0, 20)
					drawSize = int(round(math.pow(avgHGL*5, 1)))
			
			if type == 'compare_stress':
				
				if maxQperc > 0:
					fill = greyRedGradient(maxQperc+15, 0, 20)
					drawSize = int(round(math.pow(maxQperc*10, 1)))
				
				if maxQperc <= 0:
					fill = greyGreenGradient(abs(maxQperc)+15, 0, 20)
					drawSize = int(round(math.pow(maxQperc*10, 1)))
	
	#if highlighted list is provided, overide any symbology for the highlighted conduits 	
	if highlighted and id in highlighted:
		fill = blue
		drawSize = 3	
		
	drawSize = int(drawSize*xplier)
			
	#draw that thing, 
	canvas.line(coordPair, fill = fill, width = drawSize)
	if pipeLengthPlanView(coordPair[0], coordPair[1]) > drawSize*0.75:
		#if length is long enough, add circles on the ends to smooth em out
		#this check avoids circles being drawn for tiny pipe segs
		canvas.ellipse(circleBBox(coordPair[0], drawSize*0.5), fill =fill)
		canvas.ellipse(circleBBox(coordPair[1], drawSize*0.5), fill =fill)

def angleBetweenPoint(xy1, xy2):
	dx, dy = (xy2[0] - xy1[0]), (xy2[1] - xy1[1]) 
	
	angle = (math.atan(float(dx)/float(dy)) * 180/math.pi )	
	if angle < 0:
		angle = 270 - angle 
	else:
		angle = 90 - angle
	#angle in radians
	return angle

def midPoint(xy1, xy2):
	
	dx, dy = (xy2[0] + xy1[0]), (xy2[1] + xy1[1]) 
	midpt = ( int(dx/2), int(dy/2.0) )
	
	#angle in radians
	return midpt	
	
def annotateLine (img, dataDict, fontScale=1, annoKey='name', labeled = None):
	
	txt = dataDict[annoKey]
	
	if not txt in labeled:
		#do not repeat labels
		font = ImageFont.truetype(fontFile, int(25 * fontScale))
		imgTxt = Image.new('L', font.getsize(txt))
		drawTxt = ImageDraw.Draw(imgTxt)
		drawTxt.text((0,0), txt, font=font, fill=(10,10,12))
		
		coords = dataDict['coordinates']
		drawCoord = dataDict['draw_coordinates']
		angle = angleBetweenPoint(coords[0], coords[1])
		texRot = imgTxt.rotate(angle, expand=1)
		#canvas.paste( ImageOps.colorize(texRot, (0,0,0), (255,255,84)), (242,60),  texRot)
		
		midpoint = midPoint(drawCoord[0], drawCoord[1])
		#img.paste(texRot , midpoint,  texRot)
		img.paste(ImageOps.colorize(texRot, (0,0,0), (10,10,12)), midpoint,  texRot)
		labeled.append(txt) #keep tracj of whats been labeled 
	
	
		
#def drawAnnotation (canvas, inp, rpt=None, imgWidth=1024, title=None, currentTstr = None, description = None, 
#					objects = None, symbologyType=None, fill=(50,50,50), xplier=None):
def annotateMap (canvas, model, model2=None, currentTstr = None, options=None, results={}):
	
	#unpack the options
	nodeSymb = 		options['nodeSymb']
	conduitSymb = 	options['conduitSymb']
	basemap = 		options['basemap']
	parcelSymb = 	options['parcelSymb']
	traceUpNodes =	options['traceUpNodes']
	traceDnNodes =	options['traceDnNodes']
	
	modelSize = (canvas.im.getbbox()[2], canvas.im.getbbox()[3]) 
	
	#define main fonts
	fScale = 1 * modelSize[0] / 2048
	titleFont = ImageFont.truetype(fontFile, int(40 * fScale))
	font = ImageFont.truetype(fontFile, int(20 * fScale))
	
	#Buid the title and files list (handle 1 or two input models)
	#this is hideous, or elegant?
	files = title = results_string = symbology_string = annotationTxt = ""
	files = '\n'.join([m.rpt.filePath for m in filter(None, [model, model2])])
	title = ', '.join([m.inp.name for m in filter(None, [model, model2])])
	symbology_string = ', '.join([s['title'] for s in filter(None, [nodeSymb, conduitSymb, parcelSymb])])
	title += ": " + symbology_string 
	
	params_string = ''.join([" > " + str(s['threshold']*60) + "min " for s in filter(None, [parcelSymb])])
	#build the title
	
	
	#collect results
	for result, value in results.iteritems():
		results_string += result + ": " + str(value) + " "
	
	#compile the annotation text
	if results:
		annotationTxt = results_string + params_string + "\n"
	annotationTxt += "Files:\n" + files
	
	
	annoHeight = canvas.textsize(annotationTxt, font)[1] 
	
	canvas.text((10, 15), title, fill=black, font=titleFont)
	canvas.text((10, modelSize[1] - annoHeight - 10), annotationTxt, fill=black, font=font)
	
	
	if currentTstr:
		#timestamp in lower right corner
		annoHeight = canvas.textsize(currentTstr, font)[1] 
		annoWidth = canvas.textsize(currentTstr, font)[0] 
		canvas.text((modelSize[0] - annoWidth - 10, modelSize[1] - annoHeight - 10), currentTstr, fill=black, font=font)


#FONTS
fontFile = r"C:\Data\Code\Fonts\Raleway-Regular.ttf"

#end