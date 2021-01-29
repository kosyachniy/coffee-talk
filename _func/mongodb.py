# Libraries
## System
import json

## External
from pymongo import MongoClient


# Params
## Keys
with open('keys.json', 'r') as file:
	keys = json.loads(file.read())
	LOGIN = keys['mongo']['login']
	PASSWORD = keys['mongo']['password']

## Sets
with open('sets.json', 'r') as file:
	sets = json.loads(file.read())
	HOST = sets['host']
	DB = sets['mongo']['db']


# Global variables
db = MongoClient(
	host=HOST,
	port=27017,
	username=LOGIN,
	password=PASSWORD,
	authSource='admin',
	authMechanism='SCRAM-SHA-1'
)[DB]