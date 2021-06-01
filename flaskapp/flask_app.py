#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 19 18:42:02 2021

@author: giovanni.scognamiglio
"""

from flask import Flask, send_from_directory, send_file

app = Flask(__name__)

@app.route('/',methods=['GET'])
def home():
    return send_from_directory('static','home.html')

@app.route('/download/', methods=['GET'])
def download():
    return send_from_directory('static','PromoBot.exe', as_attachment=True)

@app.route('/promobot_code/', methods=['GET'])
def send_js():
    return  send_from_directory('static','promobot.py')

@app.route('/<int:number>/', methods=['GET'])
def calculate(number):
    return str(number+1)



