import os, re, pprint, time, json, pymongo
from datetime import datetime
from pymongo import MongoClient

# URL/IP regex
URL_REGEX = '(?P<url>(www.)?([a-z0-9]+\.)+[a-z]+(\/[a-zA-Z0-9#]+\/?)*)'
IP_REGEX = '(?P<ip>\d{1,3}\.\d{1,3}.\d{1,3}.\d{1,3})'

def ping(hostname, c=3):
	"""
	Calls ping on the hostname and a number of packets c.
	Stores the results and returns them
	"""
	output = os.popen('ping -c '+str(c)+' -q ' + hostname).read()
	output = output.splitlines()
	numRows = len(output)
	results = {'packets': None}
	results['timestamp'] = datetime.utcnow()
	settings = {}
	settings['hostname'] = hostname
	settings['packetsSent'] = c
	results['settings'] = settings
	if numRows > 1:
		valid = re.compile('PING '+URL_REGEX+' \('+IP_REGEX+'\): (?P<bytes>\d+) data bytes')
		match = valid.match(output[0])
		if match:
			ip = match.group('ip')
			db = match.group('bytes')
			url = match.group('url')
			resolution = {}
			resolution['ipaddr'] = ip
			resolution['numDataBytes'] = db
			resolution['url'] = url
			results['resolution'] = resolution
			if numRows > 3:
				packets = output[3]
				valid = re.compile(str(c) + ' packets transmitted, (?P<packetsRecieved>\d+) packets received, (?P<percentLoss>\d+\.\d*)% packet loss')
				match = valid.match(packets)
				if match:
					pr = match.group('packetsRecieved')
					pl = match.group('percentLoss')
					packets = {}
					packets['packetsRecieved'] = pr
					packets['packetLossRate'] = pl
					results['packets'] = packets
					if numRows > 4:
						stats = output[4]
						valid = re.compile('round-trip min/avg/max/stddev = (?P<min>\d+(\.\d+)?)/(?P<avg>\d+(\.\d+)?)/(?P<max>\d+(\.\d+)?)/(?P<stddev>\d+(\.\d+)?) ms')
						match = valid.match(stats)
						if match:
							mi = match.group('min')
							ma = match.group('max')
							avg = match.group('avg')
							stddev = match.group('stddev')
							rtt = {}
							rtt['min'] = mi
							rtt['max'] = ma
							rtt['avg'] = avg
							rtt['stddev'] = stddev
							results['rtt'] = rtt
	return results

def pingMany(urls):
	"""
	Collects the results from pinging many urls
	"""
	results = []
	for url in urls:
		results.append(ping(url))
	return results

def isValid(result, threshold):
	"""
	Checks if a ping results was valid.
	Uses a threshold from the config to define the packet loss rate that is acceptable
	"""
	packets = result['packets']
	if packets:
		percentLoss = float(packets['packetLossRate'])
		if percentLoss <= threshold:
			return True
	return False

def allValid(results, threshold):
	"""
	Returns true if at least one of the results is valid,
	otherwise if all are invalid returns false
	"""
	good = False
	for result in results:
		good = good or isValid(result, threshold)
	return good


def regexTest(value, reg):
	"""
	Tests a regex value agianst a regex
	"""
	regex = re.compile(reg)
	match = regex.match(value)
	return match

def logResults(results, db):
	"""
	Logs the ping results in the results database
	"""
	res = db.results
	ret = res.insert_many(results)

def logOutage(times, db):
	"""
	Logs the outage times in the outages database
	"""
	outages = db.outages
	ret = outages.insert_one(times)


def main():
	fo = open('urls.config', 'r').read()
	urls = fo.splitlines()
	for url in urls:
		if not regexTest(url, URL_REGEX):
			print 'Invalid url: ' + url
			return
	# Add input validation/defaults
	fo = open('config.json', 'r').read()
	config = json.loads(fo)

	client = MongoClient(config['mongoClient'], config['mongoPort'])
	db = client['qos']
	db.urls.insert_one({'urls': urls})
	db.config.insert_one(config)
	startOutage = None
	while(True):
		curs = db.urls.find({}).limit(1).sort([('$natural',-1)])
		for url in curs:
			urls = url['urls']
		curs = db.config.find().limit(1).sort([('$natural',-1)])
		for c in curs:
			config = c
		results = pingMany(urls)
		pprint.pprint(results)
		valid = allValid(results, float(config['threshold']))
		logResults(results, db)
		if valid:
			if startOutage:
				endOutage = datetime.utcnow()
				outageTime = endOutage - startOutage
				outage = {
					'start': startOutage,
					'end': endOutage,
					'delta': str(outageTime)
				}
				logOutage(outage, db)
				startOutage = None
			time.sleep(config['delayValid'])
		else:
			startOutage = datetime.utcnow()
			time.sleep(config['delayInvalid'])


if __name__ == '__main__':
	main()
