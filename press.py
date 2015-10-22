#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import sleep
from pid import PID



class Zone() :
	def __init__(self) :
		self.pid = PID()
		self.t = 0
		self.prog = [[10,12,34,5,700,5],[100,200,200,123,10,0]]

	def get_conf(self) :
		pass

	def update(self, cycle) :
		self.pid.set_point = self.get_command(cycle)
		c = self.pid.update(self.t)
		if c > 0 :
			c = min(c,self.max_heat_t)
			self.heater_off = time()+c
			self.heater = True
			self.cooler = False
		elif c < 0 :
			c = min(-c,self.max_heat_t)
			self.cooler_off = time()+c
			self.heater = False
			self.cooler = True
		pass 
	
	def off_update(self):
		if self.heater and self.heater_off < time() :
			self.heater = False
		if self.cooler and self.cooler_off < time() :
			self.cooler = False
			
		
	def get_temp(self) :
		pass	
		
	def get_command(self, cycle) :
		t = 0 
		if cycle <= 0:
			return self.prog[1][0]
		if cycle >= sum(self.prog[0])-self.prog[0][-1] :
			return self.prog[1][-1]

		for i in range(len(self.prog[0])) :
			t += self.prog[0][i]
			if t>cycle :
				break
		t1 = t - self.prog[0][i]		
		
		t_ = float(cycle - t1)/(t-t1)
#		print cycle, i, t, t1, t_,
		return float(self.prog[1][i+1] - self.prog[1][i]) * t_ + self.prog[1][i]





z = Zone()

for i in range(1000) :
	print z.get_command(i)
