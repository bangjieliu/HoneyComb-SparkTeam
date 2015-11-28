import sys
from pyspark import SparkContext
from pyspark.mllib.clustering import KMeans
from pyspark.mllib.evaluation import MulticlassMetrics
from pyspark.sql import SQLContext
from pyspark.sql import DataFrame
from numpy import array
from math import sqrt

#LogisticRegression
from pyspark.mllib.classification import LogisticRegressionWithLBFGS
from pyspark.mllib.util import MLUtils
from pyspark.mllib.evaluation import MulticlassMetrics

# Evaluate clustering by computing Within Set Sum of Squared Errors
def error(point):
    center = clusters.centers[clusters.predict(point)]
    return sqrt(sum([x**2 for x in (point - center)]))

#"/Users/jacobliu/HoneyPySpark/spark-1.5.2-bin-hadoop2.6/README.md"  # Should be some file on your system
sc = SparkContext("local", "PySpark")
SQLContext = SQLContext(sc)

loadFilePath = sys.argv[1]		#input file path
dumpFilePath = sys.argv[2]		#output file path
model_name = sys.argv[3]		#model_name

if(model_name == "KMeans"):
	# Load and parse the data
	data = sc.textFile(loadFilePath)
	parsedData = data.map(lambda line: array([float(x) for x in line.split(' ')]))
	# Build the model (cluster the data)
	clusters = KMeans.train(parsedData, 3, maxIterations=10, runs=30, initializationMode="random")

	WSSSE = parsedData.map(lambda point: error(point)).reduce(lambda x, y: x + y)
	print("Within Set Sum of Squared Error = " + str(WSSSE))

	res = [('k_means',dumpFilePath, WSSSE)]
	rdd = sc.parallelize(res)
	SQLContext.createDataFrame(rdd).collect()
	df = SQLContext.createDataFrame(rdd,['model_name','res_path', 'WSSSE'])
	df.toJSON().saveAsTextFile(dumpFilePath)

elif(model_name == "Regression"):
	# Load training data in LIBSVM format
	data = MLUtils.loadLibSVMFile(sc, loadFilePath)

	# Split data into training (60%) and test (40%)
	training, test = data.randomSplit([0.6, 0.4], seed = 11L)
	training.cache()

	# Run training algorithm to build the model
	model = LogisticRegressionWithLBFGS.train(training, numClasses=3)

	# Compute raw scores on the test set
	predictionAndLabels = test.map(lambda lp: (float(model.predict(lp.features)), lp.label))

	# Instantiate metrics object
	metrics = MulticlassMetrics(predictionAndLabels)

	# Overall statistics
	precision = metrics.precision()
	recall = metrics.recall()
	f1Score = metrics.fMeasure()
	print("Summary Stats")
	print("Precision = %s" % precision)
	print("Recall = %s" % recall)
	print("F1 Score = %s" % f1Score)

	# Statistics by class
	labels = data.map(lambda lp: lp.label).distinct().collect()
	for label in sorted(labels):
	    print("Class %s precision = %s" % (label, metrics.precision(label)))
	    print("Class %s recall = %s" % (label, metrics.recall(label)))
	    print("Class %s F1 Measure = %s" % (label, metrics.fMeasure(label, beta=1.0)))

	# Weighted stats
	print("Weighted recall = %s" % metrics.weightedRecall)
	print("Weighted precision = %s" % metrics.weightedPrecision)
	print("Weighted F(1) Score = %s" % metrics.weightedFMeasure())
	print("Weighted F(0.5) Score = %s" % metrics.weightedFMeasure(beta=0.5))
	print("Weighted false positive rate = %s" % metrics.weightedFalsePositiveRate)

	#save output file path as JSON and dump into dumpFilePath
	res = [('regression',dumpFilePath, precision, recall, f1Score)]
	rdd = sc.parallelize(res)
	SQLContext.createDataFrame(rdd).collect()
	df = SQLContext.createDataFrame(rdd,['model_name','res_path', 'precision', 'recall', 'f1Score'])
	df.toJSON().saveAsTextFile(dumpFilePath)




#SQLContext = SQLContext(sc)
#res = [('k_means',dumpFilePath)]
#rdd = sc.parallelize(res)
#SQLContext.createDataFrame(rdd).collect()
#df = SQLContext.createDataFrame(rdd,['model_name','res_path'])
#df.toJSON().saveAsTextFile(dumpFilePath)


# Save and load model
#clusters.save(sc, "myModel")
#sameModel = KMeansModel.load(sc, "myModel")