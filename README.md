There are two portions to this program.
1. The code that runs constantly calling ping and recording the results in the mongo database
2. The webserver that opens up RESTful APIs to the mongo database data.

Installation
1. Install mongodb
	a. Download mongodb from skdfsldfj and follow instructions
	b. add mongod to the PATH
2. Make sure python 2.x and pip are installed
3. Run `sudo pip install requirements.txt`
4. Run python pinger/pinger.py
5. Run python webserver/run.py
6. Navigate to localhost:5000/results to check some values are returned