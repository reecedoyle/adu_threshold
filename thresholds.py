import json
import urllib2
import sys

def getThreshold(percentage, points):
	sorted(points)
	index = len(points) - int((len(points)*(percentage/100)))
	return (points[index] + points[index-1])/2

def avg(a):
	return sum(a)/len(a)

def getData():
	#read commandline args
	startTime = sys.argv[1] # in unix time format

	# Acquire data from REST API
	url = 'http://178.62.40.4/api/readings-unixtime?start='+str(startTime)
	resp = urllib2.urlopen(url)
	return json.loads(resp.read())

def createAnomalyScoreList(data):
	# create list of anomaly scores for all points in data
	anomalyscores = []
	for x in data["readings"]:
		if "anomalyScore" in x:
			anomalyscores.append(x["anomalyScore"])
	return anomalyscores

def createFeedbackList(data):
	#create list of tuples, containing anomaly scores with feedback in the form (score,classification,feedback)
	feedBackPoints = [] 
	for x in data["readings"]:
		if "anomalyScore" in x and "classification" in x:
			if "feedback" in x:
				feedBackPoints.append((x["anomalyScore"], x["classification"], x["feedback"]))

	return feedBackPoints

def splitFeedbackList(feedBackPoints):
	# Split the points with feedback into seperate categories, based on classification and user's feed back. eg: Classifier: Amber, Feedback: red
	GR = []
	GA = []
	AR = []
	AG = []
	RA = []
	RG = []

	for x in feedBackPoints:
		if x[1] == "green":
			if x[2] == "red":
				GR.append(x[0])
				continue
			if x[2] == "amber":
				GA.append(x[0])
				continue
		if x[1] == "amber":
			if x[2] == "red":
				AR.append(x[0])
				continue
			if x[2] == "green":
				AG.append(x[0])
				continue

		if x[1] == "red":
			if x[2] == "amber":
				RA.append(x[0])
				continue
			if x[2] == "green":
				RG.append(x[0])
				continue

	return (GR,GA,AR,AG,RA,RG)


def formulaUP(score, threshold):
	return (BASE_INCREASE_MULTIPLIER*((FORMULA_UP_CONST/score) - threshold))

def formulaDOWN(score, threshold):
	return	(BASE_DECREASE_MULTIPLIER/((FORMULA_DOWN_CONST/score) - threshold))  

def calculateNewThresholds(feedbackList, redThresh, amberThresh):
	fsplits = splitFeedbackList(feedbackList)
	avgFSplits = (avg(fsplits[0]),avg(fsplits[1]),avg(fsplits[2]),avg(fsplits[3]),avg(fsplits[4]),avg(fsplits[5]))
	lenFSplits = (len(fsplits[0]),len(fsplits[1]),len(fsplits[2]),len(fsplits[3]),len(fsplits[4]),len(fsplits[5]))
	redmultipliers = []
	ambermultipliers = []

	#scenario 1
	redmultipliers.append(formulaDOWN(avgFSplits[0],prevRedThresh))
	ambermultipliers.append(redmultipliers[0])

	#scenario 2
	ambermultipliers.append(formulaDOWN(avgFSplits[1],prevAmberThresh))

	#scenario 3
	redmultipliers.append(formulaDOWN(avgFSplits[2],prevRedThresh))
	
	#scenario 4
	ambermultipliers.append(formulaUP(avgFSplits[3],prevAmberThresh))

	#scenario 5
	redmultipliers.append(formulaUP(avgFSplits[4],prevRedThresh))
	
	#secnario 6
	redmultipliers.append(formulaUP(avgFSplits[5],prevRedThresh))
	ambermultipliers.append(redmultipliers[3])

	newRedThreshold = 0
	newAmberThreshold = 0

	newRedThreshold+=lenFSplits[0]*redmultipliers[0]
	newRedThreshold+=lenFSplits[2]*redmultipliers[1]
	newRedThreshold+=lenFSplits[4]*redmultipliers[2]
	newRedThreshold+=lenFSplits[5]*redmultipliers[3]

	newAmberThreshold+=lenFSplits[0]*ambermultipliers[0]
	newAmberThreshold+=lenFSplits[1]*ambermultipliers[1]
	newAmberThreshold+=lenFSplits[3]*ambermultipliers[2]
	newAmberThreshold+=lenFSplits[5]*ambermultipliers[3]

	newRedThreshold/=(sum(lenFSplits)-(lenFSplits[1]+lenFSplits[3]))
	newAmberThreshold/=(sum(lenFSplits)-(lenFSplits[2]+lenFSplits[4]))

	newRedThreshold = (newRedThreshold+prevRedThresh)/2
	newAmberThreshold = (newAmberThreshold+prevAmberThresh)/2

	return (newRedThreshold,newAmberThreshold)

def getAutoThresh(scores):
	newRedThresh = prevRedThresh + (prevRedThresh - getThreshold(redPercent, anomalyscores))/2
	newAmberThresh = prevAmberThresh + (prevAmberThresh - getThreshold(amberPercent, anomalyscores))/2
	return newAmberThresh, newRedThresh


#								Execution begins here
########################################################################################
BASE_INCREASE_MULTIPLIER = 1.2
BASE_DECREASE_MUTIPLIER = 0.8
FORMULA_UP_CONST = 1.0
FORMULA_DOWN_CONST = 1.0

redPercent = float(sys.argv[2])
amberPercent = float(sys.argv[3])
prevRedThresh = float(sys.argv[4])
prevAmberThresh = float(sys.argv[5])

data = getData()
anomalyscores = createAnomalyScoreList(data)
feedbackList = createFeedbackList(data)
#move towards true threshold by half
newAmberThresh, newRedThresh = getAutoThresh(anomalyscores)

#add some code to pass these calculated values to system
#print "amber is "+ str(newAmberThreshold) + " red is "+str(newRedThreshold)
#print "amber percentage is "+ str(currentAmberPercentage) + " red percentage is " +str(currentRedPercentage)
if(len(feedbackList)!=0):
	newThresholds = calculateNewThresholds(feedbackList, newRedThresh, newAmberThresh)
	#print "amber is "+ str(newThresholds[1]) + " red is "+ str(newThreholds[0])



